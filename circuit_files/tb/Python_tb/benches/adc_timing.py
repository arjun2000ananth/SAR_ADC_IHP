"""Full ADC: conversion timing (sampling window, bit cycles, latency, max fs), back-to-back check, power."""
from __future__ import annotations

import math

import numpy as np

from sartb import wave
from sartb.adc import AdcEngine
from sartb.spice import run_many

from .common import plt, run_dir


def add_args(p):
    p.add_argument("--variant", choices=["real", "ideal"], default="real",
                   help="ideal = ideal sampling/DAC switches (FSM + comparator + caps only)")
    p.add_argument("--fsm-model", choices=["xspice", "spice"], default=None,
                   help="FSM simulation model (default config FSM_MODEL); spice = transistor-level std-cells")
    p.add_argument("--probe-period", type=float, default=None,
                   help="START period for the first (timing) run; default max(2us, 2/FS_TARGET)")


def measure(eng, res, n, c):
    """Per-conversion timing from a probe run with internal nodes saved."""
    d = res.data("adc.txt")
    t = d["t"]
    vt = c.VDD / 2                  # sample / comp_clk: 3.3 V side (after the level shifters)
    vtd = eng.dom.vdig / 2          # valid / busy: FSM (1.2 V) domain
    P = c.ADC_PORTS
    ai = c.ADC_INTERNAL
    smp = d[f"v(x1.{ai['sample']})"]
    cck = d[f"v(x1.{ai['comp_clk']})"]
    s_r, s_f = wave.crossings(t, smp, vt, "rise"), wave.crossings(t, smp, vt, "fall")
    c_r, c_f = wave.crossings(t, cck, vt, "rise"), wave.crossings(t, cck, vt, "fall")
    v_f = wave.crossings(t, d[f"v({P['valid']})"], vtd, "fall")
    b_r = wave.crossings(t, d[f"v({P['busy']})"], vtd, "rise")
    b_f = wave.crossings(t, d[f"v({P['busy']})"], vtd, "fall")
    parsed = eng.parse(res, n)
    rows = []
    for j in range(n):
        ts = eng.t_start(j)
        te = ts + eng.t_conv
        r = {"t_start": ts, "code": parsed[j]["code"], "latency": parsed[j]["latency"],
             "n_valid": parsed[j]["n_valid"]}
        sf = s_f[(s_f > ts) & (s_f < te)]
        r["t_sf_rel"] = float(sf[0] - ts) if len(sf) else float("nan")
        if len(sf):
            sr = s_r[s_r < sf[0]]
            r["t_sr_rel"] = float(sr[-1] - ts) if len(sr) else float("nan")
        else:
            r["t_sr_rel"] = float("nan")
        r["t_sample"] = r["t_sf_rel"] - r["t_sr_rel"]
        tv = ts + r["latency"] if not math.isnan(r["latency"]) else te
        cr = c_r[(c_r > ts) & (c_r < tv)]
        cf = c_f[(c_f > ts) & (c_f < tv + c.TCLK)]
        r["n_comp"] = int(len(cr))
        r["comp_period"] = float(np.median(np.diff(cr))) if len(cr) > 1 else float("nan")
        if len(cr) and len(cf):
            widths = [float(cf[cf > x][0] - x) for x in cr if np.any(cf > x)]
            r["comp_high"] = float(np.median(widths)) if widths else float("nan")
        else:
            r["comp_high"] = float("nan")
        vf = v_f[v_f > tv]
        r["valid_width"] = float(vf[0] - tv) if len(vf) and not math.isnan(r["latency"]) else float("nan")
        br = b_r[(b_r > ts - c.TCLK) & (b_r < te)]
        bf = b_f[(b_f > ts) & (b_f < te)]
        r["busy_end_rel"] = float(bf[0] - ts) if len(bf) else float("nan")
        r["busy_start_rel"] = float(br[0] - ts) if len(br) else float("nan")
        rows.append(r)
    return rows


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    rd = run_dir(ctx)
    tp = a.probe_period or max(2e-6, 2.0 / c.FS_TARGET)
    tp = math.ceil(tp / c.TCLK) * c.TCLK
    fm = a.fsm_model or c.FSM_MODEL
    eng = AdcEngine(ctx, a.variant, t_conv=tp, label="probe", fsm_model=fm)
    fsm = ctx.lib.get(c.FSM_SUBCKT)
    dom = eng.dom
    rep.note(f"FSM from {fsm.source}, simulated as {eng.fsm_model}; variant={a.variant}")
    rep.note("voltage domains: " + dom.describe())
    for n in dom.notes:
        rep.note(n)
    if eng.fsm_model == "xspice":
        rep.note("FSM is the XSPICE logic model: the std-cells' own switching power is NOT in the 1.2 V "
                 "power (level shifters are transistor-level and are included); "
                 "--fsm-model spice gives full transistor-level power")
    supply_check(rep, c, fsm, dom)

    # ---- 1. probe with long START period ------------------------------------
    vals = [0.37 * c.VFS / 2, -0.61 * c.VFS / 2, c.LSB * 0.5]
    d = eng.deck(len(vals), dc_values=vals, save_internal=True, currents=True, save_step=0.1e-9,
                 title="timing probe")
    (res,) = run_many(c, [(d, "probe")], rd, "probe")
    rows = measure(eng, res, len(vals), c)
    ideal = eng.ideal_code(vals)
    r0 = rows[0]
    for k, r in enumerate(rows):
        rep.data.setdefault("probe", []).append(r)
    ok = [r for r in rows if r["code"] >= 0]
    if not ok:
        rep.add("conversions with valid", 0, "", len(rows), ">=")
        rep.note("no `valid` pulse seen - check RSTN/START polarity, CLK, FSM netlist")
        _plot(ctx, eng, res, 0)
        return
    lat = float(np.nanmax([r["latency"] for r in rows]))
    t_s = float(np.nanmedian([r["t_sample"] for r in rows]))
    t_sf = float(np.nanmedian([r["t_sf_rel"] for r in rows]))
    t_sr = float(np.nanmedian([r["t_sr_rel"] for r in rows]))
    ncomp = int(np.median([r["n_comp"] for r in rows]))
    busy_end = float(np.nanmax([r["busy_end_rel"] for r in rows]))
    vw = float(np.nanmedian([r["valid_width"] for r in rows]))
    end_rel = np.nanmax([lat + (vw if not math.isnan(vw) else c.TCLK),
                         busy_end if not math.isnan(busy_end) else 0])
    n_min = int(math.ceil(end_rel / c.TCLK)) + 1
    t_min = n_min * c.TCLK

    rep.add("conversions with valid (probe)", len(ok), "", len(rows), ">=")
    rep.add("latency START->valid", lat, "s")
    rep.add("sampling window", t_s, "s", desc="sample high time")
    rep.add("sample rise rel. START", t_sr, "s")
    rep.add("sample fall rel. START", t_sf, "s")
    rep.add("comparator clocks / conversion", ncomp, "", (c.NBITS, c.NBITS + 1), "range")
    rep.add("comp_clk period", r0["comp_period"], "s")
    rep.add("comp_clk high time", r0["comp_high"], "s")
    rep.add("DAC settling window (comp_clk low)", r0["comp_period"] - r0["comp_high"], "s",
            desc="used as the settling budget by dac_switch / cdac / cap_drivers")
    rep.add("valid pulse width", vw, "s")
    rep.add("min conversion period", t_min, "s", desc=f"{n_min} CLK cycles")
    rep.add("max sample rate", 1 / t_min, "S/s", c.FS_TARGET, ">=")
    # in-situ disturbance of vcp-vcn right at the comparator evaluation edges
    dd0 = res.data("adc.txt")
    ai = c.ADC_INTERNAL
    vdt = dd0[f"v(x1.{ai['vcp']})"] - dd0[f"v(x1.{ai['vcn']})"]
    ce = wave.crossings(dd0["t"], dd0[f"v(x1.{ai['comp_clk']})"], c.VDD / 2, "rise")
    # in-situ level-shifter delays (1.2 V FSM side -> 3.3 V analog side and back)
    ls_delays: dict[str, list] = {}
    if dom.mode == "generated":
        for net, direction in ((ai["comp_clk"], "up"), (ai["sample"], "up"), (ai["voutp"], "down")):
            lo, hi = f"v(x1.{net}_lv)", f"v(x1.{net})"
            if lo not in dd0 or hi not in dd0:
                continue
            src, dst = (lo, hi) if direction == "up" else (hi, lo)
            vs = dom.vdig / 2 if direction == "up" else c.VDD / 2
            vdst = c.VDD / 2 if direction == "up" else dom.vdig / 2
            dl = []
            for edge in ("rise", "fall"):
                for x in wave.crossings(dd0["t"], dd0[src], vs, edge)[:20]:
                    y = wave.first_crossing(dd0["t"], dd0[dst], vdst, edge, x, x + 5e-9)
                    if not math.isnan(y):
                        dl.append(y - x)
            if dl:
                ls_delays.setdefault(direction, []).extend(dl)
                what = f"{net}: 1.2->3.3 V shifter" if direction == "up" else f"{net}: 3.3->1.2 V buffer"
                rep.add(f"in-situ delay {what}", float(np.max(dl)), "s",
                        desc=f"worst of {len(dl)} edges, spread {1e12 * (max(dl) - min(dl)):.0f} ps")
    if len(ce):
        kicks = [wave.value_at(dd0["t"], vdt, x + 0.3e-9) - wave.value_at(dd0["t"], vdt, x - 0.2e-9) for x in ce]
        rep.add("top-plate kick at comparator edge (max)", float(np.max(np.abs(kicks))) / c.LSB, "LSB", 0.25, "<=",
                "vcp-vcn 0.3 ns after comp_clk rises minus 0.2 ns before; the comparator decides on this")
        rep.data["edge_kicks_lsb"] = (np.array(kicks) / c.LSB).tolist()
    for k, (r, ic) in enumerate(zip(rows, ideal)):
        rep.add(f"probe {k}: code (ideal {ic})", r["code"], "", (ic - 2, ic + 2), "range",
                f"Vdiff={vals[k]:+.4f} V")
    _plot(ctx, eng, res, 0)

    # ---- 2. back-to-back at the operating period ----------------------------
    if c.CONV_PERIOD_CLK:
        n_op = int(c.CONV_PERIOD_CLK)
        src = "config CONV_PERIOD_CLK"
    else:
        n_tgt = int(round(c.FCLK / c.FS_TARGET))
        n_op = n_tgt if n_tgt >= n_min else n_min
        src = "FS_TARGET" if n_tgt >= n_min else "minimum period (FS_TARGET not reachable)"
    t_op = n_op * c.TCLK
    eng2 = AdcEngine(ctx, a.variant, t_conv=t_op, t_sf_rel=t_sf, label="b2b", fsm_model=fm)
    vals2 = vals + vals
    d2 = eng2.deck(len(vals2), dc_values=vals2, currents=True, save_step=0.2e-9, title="back-to-back")
    (res2,) = run_many(c, [(d2, "b2b")], rd, "back-to-back")
    p2 = eng2.parse(res2, len(vals2))
    codes2 = [p["code"] for p in p2]
    rep.add("operating conversion period", t_op, "s", desc=f"{n_op} CLK ({src})")
    rep.add("operating sample rate", 1 / t_op, "S/s")
    same = sum(1 for k in range(len(vals)) if codes2[k] == rows[k]["code"] and codes2[k + 3] == rows[k]["code"])
    rep.add("back-to-back codes == probe codes", same, "", len(vals), ">=",
            "catches state leaking from one conversion into the next")
    missing = sum(1 for p in p2 if p["code"] < 0)
    rep.add("missing valid (back-to-back)", missing, "", 0, "<=")

    # power over two steady-state periods
    dd = res2.data("adc.txt")
    t = dd["t"]
    ta, tb = eng2.t_start(2), eng2.t_start(4)
    def pw(src, v):   # average power from the charge integrator: Q = 1nF * V(q)
        q = dd[f"v(q_{src})"]
        dq = (wave.value_at(t, q, tb) - wave.value_at(t, q, ta)) * 1e-9
        return -v * dq / (tb - ta)
    p_vdd, p_ref, p_cm = pw("vvdd", c.VDD), pw("vvref", c.VREFP), pw("vvcm", c.VCM)
    p_lv = pw("vvddlv", c.VDD_LV) if dom.lv_port else 0.0
    p_tot = p_vdd + p_ref + p_cm + p_lv
    rep.add("power VDD (3.3 V analog)", p_vdd, "W")
    if dom.lv_port:
        rep.add("power VDD_LV (1.2 V FSM + shifters)", p_lv, "W")
    rep.add("power VREFP", p_ref, "W")
    rep.add("power VCM source", p_cm, "W", desc="positive = VCM source delivers power")
    rep.add("total power", p_tot, "W")
    rep.add("energy / conversion", p_tot * t_op, "J")

    rep.data["timing"] = {"t_conv_period": t_op, "n_clk_period": n_op, "t_conv_min": t_min,
                          "latency": lat, "t_sample": t_s, "t_sf_rel": t_sf, "t_sr_rel": t_sr,
                          "n_comp": ncomp, "energy_per_conv": p_tot * t_op, "power": p_tot,
                          "t_comp_high": r0["comp_high"],
                          "t_dac": (r0["comp_period"] - r0["comp_high"]) if not math.isnan(r0["comp_period"])
                          else None,
                          "ls_up_delay": float(np.mean(ls_delays["up"])) if ls_delays.get("up") else None,
                          "ls_down_delay": float(np.mean(ls_delays["down"])) if ls_delays.get("down") else None,
                          "variant": a.variant, "fsm_model": eng.fsm_model, "domain_mode": dom.mode,
                          "vdig": dom.vdig}


def _plot(ctx, eng, res, j):
    c = ctx.cfg
    d = res.data("adc.txt")
    t = d["t"]
    ts = eng.t_start(j)
    m = (t > ts - 0.1 * eng.t_conv) & (t < ts + 0.9 * eng.t_conv)
    ai = c.ADC_INTERNAL
    fig, ax = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    tt = (t[m] - ts) * 1e9
    ax[0].plot(tt, d[f"v({c.ADC_PORTS['start']})"][m], label=f"START ({eng.dom.vdig} V)")
    ax[0].plot(tt, d[f"v(x1.{ai['sample']})"][m] + 0.05, label="sample")
    ax[0].plot(tt, d[f"v(x1.{ai['comp_clk']})"][m] + 0.1, label="comp_clk")
    P = c.ADC_PORTS
    ax[0].plot(tt, d[f"v({P['busy']})"][m] + 0.15, label=f"busy ({eng.dom.vdig} V)")
    ax[0].plot(tt, d[f"v({P['valid']})"][m] + 0.2, label=f"valid ({eng.dom.vdig} V)")
    ax[0].legend(ncol=5, fontsize=8)
    ax[0].set_ylabel("V")
    vd = d[f"v(x1.{ai['vcp']})"] - d[f"v(x1.{ai['vcn']})"]
    ax[1].plot(tt, vd[m], label="vcp - vcn")
    ax[1].plot(tt, (d["v(ainp)"] - d["v(ainn)"])[m], "--", label="ainp - ainn")
    ax[1].set_ylabel("V")
    ax[1].legend(fontsize=8)
    ax[2].plot(tt, d[f"v(x1.{ai['vcp']})"][m], label="vcp")
    ax[2].plot(tt, d[f"v(x1.{ai['vcn']})"][m], label="vcn")
    ax[2].plot(tt, d[f"v(x1.{ai['voutp']})"][m] * 0.2, label="Voutp x0.2")
    ax[2].legend(fontsize=8)
    ax[2].set_ylabel("V")
    for i in range(c.NBITS):
        ax[3].plot(tt, d[f"v(x1.dbp{i})"][m] / c.VDD * 0.4 + i, c="C0", lw=0.8)
        ax[3].plot(tt, d[f"v(x1.dbn{i})"][m] / c.VDD * 0.4 + i + 0.45, c="C3", lw=0.8)
    ax[3].set_yticks(range(c.NBITS))
    ax[3].set_ylabel("dbp (blue) / dbn (red) bit")
    ax[3].set_xlabel("t - START [ns]")
    fig.suptitle(f"conversion {j} (variant={eng.variant})")
    fig.tight_layout()
    ctx.rep.plot(fig, f"conversion_{eng.variant}.png")


def supply_check(rep, c, fsm, dom):
    """1.2 V std-cells must not see 3.3 V."""
    cells = {m.lower() for _, m in fsm.instances}
    if any(m.startswith("sg13cmos5l_") for m in cells):
        rep.add("FSM std-cell supply", dom.fsm_supply, "V", (0, 1.32), "warn-range",
                "sg13cmos5l cells are 1.2 V (thin-oxide) devices")
        if dom.fsm_supply > 1.32:
            rep.note(f"FSM std-cells run from {dom.fsm_supply} V as drawn: simulation works, silicon would be "
                     f"overstressed. Set FSM_DOMAIN='lv' (default) or give sar_10_bit a 1.2 V supply port")
