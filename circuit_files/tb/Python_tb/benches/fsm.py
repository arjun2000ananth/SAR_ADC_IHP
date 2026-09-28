"""SAR FSM (sar_fsm_wrapper): XSPICE-model equivalence, closed-loop codes with ideal switches, bit-cycle timing."""
from __future__ import annotations

import math
import random

import numpy as np

from sartb import wave
from sartb.adc import AdcEngine
from sartb.spice import Deck, fmt, run_many
from sartb.xspice_fsm import XspiceConverter

from .adc_timing import measure, supply_check
from .common import adc_timing, instance_line, run_dir


def add_args(p):
    p.add_argument("--no-equiv", action="store_true", help="skip the transistor-vs-XSPICE equivalence run")
    p.add_argument("--equiv-time", type=float, default=1.2e-6, help="length of the equivalence run")
    p.add_argument("--nrandom", type=int, default=12, help="random codes in the closed-loop test")


def _fsm_deck(ctx, xs_text, tstop, voutp_period, vdig):
    from sartb.domains import fsm_port_dirs, fsm_roles
    c = ctx.cfg
    fsm = ctx.lib.get(c.FSM_SUBCKT)
    roles = fsm_roles(ctx.lib, c)                 # ADC-top net - FSM port (by position)
    dirs = fsm_port_dirs(ctx.lib, c)
    port = {k.lower(): v for k, v in roles.items()}
    P = c.ADC_PORTS
    clk, rst, start = port[P["clk"].lower()], port[P["rstn"].lower()], port[P["start"].lower()]
    comp = port[c.ADC_INTERNAL["voutp"].lower()]
    d = Deck(c, ctx.lib, "fsm equivalence")
    d.use(c.FSM_SUBCKT)
    if xs_text:
        d.override(c.FSM_SUBCKT, xs_text)
    d.add(instance_line("x1", fsm, {p: p for p in fsm.ports}))
    t_start = (math.ceil(c.T_RSTN / c.TCLK) + 2 + c.START_PHASE) * c.TCLK
    d.add(f"Vclk {clk} 0 PULSE(0 {vdig} 0 {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} {fmt(c.TCLK / 2 - c.T_EDGE)} {fmt(c.TCLK)})",
          f"Vrstn {rst} 0 PWL(0 0 {fmt(c.T_RSTN)} 0 {fmt(c.T_RSTN + c.T_EDGE)} {vdig})",
          f"Vstart {start} 0 PULSE(0 {vdig} {fmt(t_start)} {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} "
          f"{fmt(c.START_WIDTH_CLK * c.TCLK)} {fmt(tstop / 2)})",
          # pseudo-random comparator answers, changing mid-way through CLK-low phases
          f"Vcomp {comp} 0 PULSE(0 {vdig} {fmt(0.75 * c.TCLK)} 100p 100p {fmt(voutp_period * 0.37)} "
          f"{fmt(voutp_period)})")
    for p in fsm.ports:
        if dirs[p] == "supply":
            d.add(f"Vsup_{p} {p} 0 {vdig if p.lower() in ('vdd', 'vpwr') else 0}")
    outs = [p for p in fsm.ports if dirs[p] == "out"]
    for p in outs:
        d.add(f"Cl_{p} {p} 0 5f")
    d.control(f"tran {fmt(c.TCLK / 200)} {fmt(tstop)} 0 {fmt(c.TCLK / 100)}")
    d.wrdata("o.txt", [f"v({p})" for p in outs])
    return d, outs


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    rd = run_dir(ctx)
    fsm = ctx.lib.get(c.FSM_SUBCKT)
    cells = [m.lower() for _, m in fsm.instances]
    rep.note(f"FSM netlist: {fsm.source}  ({len(fsm.instances)} instances, ports: {' '.join(fsm.ports)})")
    rep.add("FSM std-cell instances", len(cells))
    from sartb.domains import build, fsm_roles
    dom = build(c, ctx.lib)
    supply_check(rep, c, fsm, dom)
    rep.note("voltage domains: " + dom.describe())
    rep.data["pin_roles"] = fsm_roles(ctx.lib, c)

    # XSPICE model vs transistor-level FSM
    from sartb.xspice_fsm import LibertyError
    xs = XspiceConverter(c, ctx.lib, c.STDCELL_LIB, c.XSPICE_GATE_DELAY, c.XSPICE_CLK2Q, c.XSPICE_TRF,
                         vdd=dom.fsm_supply)
    try:
        xs_text = xs.convert(c.FSM_SUBCKT)
        with open(f"{ctx.out_dir}/sar_fsm_wrapper_xspice.sp", "w") as f:
            f.write(xs_text)
        fm = "xspice"
    except (LibertyError, OSError) as e:
        rep.note(f"XSPICE model not possible: {e} -> set FSM_MODEL='spice' (slow but exact)")
        xs_text, fm = None, "spice"
    if not a.no_equiv and xs_text:
        tstop = 0.6e-6 if a.quick else a.equiv_time
        d1, outs = _fsm_deck(ctx, None, tstop, 7.3 * c.TCLK, dom.fsm_supply)
        d2, _ = _fsm_deck(ctx, xs_text, tstop, 7.3 * c.TCLK, dom.fsm_supply)
        r1, r2 = run_many(c, [(d1, "equiv_spice"), (d2, "equiv_xspice")], rd, "FSM equivalence")
        s1, s2 = r1.data(), r2.data()
        tq = np.arange(c.TCLK * 0.75, tstop, c.TCLK)       # middle of each CLK-low phase
        mism = {}
        for p in outs:
            b1 = wave.value_at(s1["t"], s1[f"v({p})"], tq) > dom.fsm_supply / 2
            b2 = wave.value_at(s2["t"], s2[f"v({p})"], tq) > dom.fsm_supply / 2
            if np.any(b1 != b2):
                mism[p] = int(np.sum(b1 != b2))
        rep.add("XSPICE vs transistor FSM mismatches", sum(mism.values()), "", 0, "<=",
                f"{len(outs)} outputs x {len(tq)} clock cycles; spice {r1.elapsed:.0f}s vs xspice {r2.elapsed:.1f}s")
        if mism:
            rep.note(f"XSPICE model differs on: {mism} -> use FSM_MODEL='spice' for ADC runs")
        toggles = sum(int(np.sum(np.abs(np.diff((s1[f'v({p})'] > dom.fsm_supply / 2).astype(int)))))
                      for p in outs)
        rep.add("output toggles seen in equivalence run", toggles, "", 1, ">=",
                "0 would mean the FSM never left reset")

    # closed loop with ideal switches
    tim = adc_timing(c)
    t_conv = tim.get("t_conv_period") or max(2e-6, 2 / c.FS_TARGET)
    t_conv = math.ceil(t_conv / c.TCLK) * c.TCLK
    eng = AdcEngine(ctx, "ideal", t_conv=t_conv, t_sf_rel=tim.get("t_sf_rel"), label="fsm", fsm_model=fm)
    # timing detail run with internal nodes
    vals_t = [0.37 * c.VFS / 2, -0.61 * c.VFS / 2]
    dt = eng.deck(len(vals_t), dc_values=vals_t, save_internal=True, save_step=0.1e-9, title="fsm timing")
    (rt,) = run_many(c, [(dt, "timing_ideal")], rd, "timing")
    rows = measure(eng, rt, len(vals_t), c)
    r0 = rows[0]
    rep.add("comparisons per conversion", r0["n_comp"], "", (c.NBITS, c.NBITS + 1), "range")
    rep.add("sampling window", r0["t_sample"], "s")
    rep.add("latency START->valid", r0["latency"], "s")
    rep.add("comp_clk period", r0["comp_period"], "s")
    rep.add("comp_clk high (comparator evaluate time)", r0["comp_high"], "s")
    dac_time = r0["comp_period"] - r0["comp_high"] if not math.isnan(r0["comp_period"]) else float("nan")
    rep.add("DAC settling window (comp_clk low)", dac_time, "s",
            desc="time between comparator reset and next evaluation")

    rnd = random.Random(1)
    codes = [0, 1, 2, 3, 127, 128, 255, 256, 383, 511, 512, 513, 640, 767, 768, 895, 1020, 1021, 1022, 1023]
    codes = [k for k in codes if k < c.NCODES]
    if a.quick:
        codes = [1, 255, 511, 512, 768, 1022]
    else:
        codes += [rnd.randrange(c.NCODES) for _ in range(a.nrandom)]
    vin = [-c.VFS / 2 + (k + 0.5) * c.LSB for k in codes]
    got = eng.convert(vin, "closed_loop", rd)
    exact = int(np.sum(got == np.array(codes)))
    rep.add("codes correct (ideal switches, buffered comparator)", exact, "", len(codes), ">=",
            "inputs at code centres, expected code = floor((Vd+VFS/2)/LSB)")
    diag = _diagnose(np.array(codes), got, c.NBITS)
    if diag:
        rep.note("code mismatch pattern: " + diag)
    rep.data["closed_loop"] = [{"expected": int(e), "got": int(g)} for e, g in zip(codes, got)]
    if len(got):
        rep.add("max |code error|", int(np.max(np.abs(got - np.array(codes)))), "codes", 1, "<=")

    _plot(ctx, eng, rt)


def _diagnose(exp, got, nb):
    if np.all(got == exp):
        return ""
    msgs = []
    if np.any(got < 0):
        msgs.append(f"{int(np.sum(got < 0))} conversions produced no `valid`")
    ok = got >= 0
    e, g = exp[ok], got[ok]
    if len(e) and np.all(g == (2 ** nb - 1) - e):
        msgs.append("codes are inverted (1023-k): swap Voutp polarity or C bits")
    rev = np.array([int(f"{x:0{nb}b}"[::-1], 2) for x in e])
    if len(e) and np.all(g == rev):
        msgs.append("bit order reversed: C0 is the MSB? fix CODE_BITS in config.py")
    d = g - e
    if len(d) and np.all(d == d[0]):
        msgs.append(f"constant offset of {int(d[0])} codes (transition convention?)")
    if len(d) and not msgs:
        msgs.append(f"errors {sorted(set(d.tolist()))}")
    return "; ".join(msgs)


def _plot(ctx, eng, res):
    from .adc_timing import _plot as tplot
    tplot(ctx, eng, res, 0)
