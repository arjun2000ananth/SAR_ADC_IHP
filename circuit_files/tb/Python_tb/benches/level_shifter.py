"""Level shifters: 1.2->3.3 V (delays, duty, static current, min VDDL, fmax) and the 3.3->1.2 V buffer into the FSM."""
from __future__ import annotations

import numpy as np

from sartb import wave
from sartb.spice import fmt, run_many

from .common import deck, instance_line, plt, run_dir


def add_args(p):
    p.add_argument("--dut", default="level_shifter_1v2_to_3v3")
    p.add_argument("--cload", type=float, default=10e-15)
    p.add_argument("--freq", type=float, default=None, help="test frequency (default FCLK)")


def _deck(ctx, sc, vddl, freq, cload, ncyc=4, title="ls"):
    c = ctx.cfg
    T = 1 / freq
    d = deck(ctx, title)
    d.use(sc.name)
    d.add(f"Vvddl vddl 0 {vddl}", f"Vvddh vddh 0 {c.VDD}", "Vvss vss 0 0",
          f"Vin in 0 PULSE(0 {vddl} {fmt(T / 4)} {fmt(min(100e-12, T / 20))} {fmt(min(100e-12, T / 20))} "
          f"{fmt(T / 2 - min(100e-12, T / 20))} {fmt(T)})")
    d.add(instance_line("xdut", sc, {"vddl": "vddl", "vddh": "vddh", "out": "out", "vss": "vss", "in": "in"}))
    d.add(f"Cl out 0 {cload}")
    d.control(f"tran {fmt(T / 1000)} {fmt(ncyc * T)}")
    d.wrdata("o.txt", ["v(in)", "v(out)", "i(vvddh)", "i(vvddl)"])
    return d, T


def analyse(dat, T, vddl, vddh, ncyc):
    t, vi, vo = dat["t"], dat["v(in)"], dat["v(out)"]
    tin_r = wave.crossings(t, vi, vddl / 2, "rise", T)
    tin_f = wave.crossings(t, vi, vddl / 2, "fall", T)
    to_r = wave.crossings(t, vo, vddh / 2, "rise", T)
    to_f = wave.crossings(t, vo, vddh / 2, "fall", T)
    res = {"ok": False}
    if len(tin_r) and len(tin_f) and len(to_r) and len(to_f):
        # non-inverting?  output edge following the first input rising edge
        nr = to_r[to_r > tin_r[0]]
        nf = to_f[to_f > tin_r[0]]
        inverting = len(nf) and (not len(nr) or nf[0] < nr[0])
        if inverting:
            tplh = float(to_r[to_r > tin_f[0]][0] - tin_f[0]) if np.any(to_r > tin_f[0]) else np.nan
            tphl = float(nf[0] - tin_r[0])
        else:
            tplh = float(nr[0] - tin_r[0])
            tphl = float(to_f[to_f > tin_f[0]][0] - tin_f[0]) if np.any(to_f > tin_f[0]) else np.nan
        hi = (t > (ncyc - 1) * T) & (t < ncyc * T)
        vmax, vmin = float(vo[hi].max()), float(vo[hi].min())
        res = {"ok": vmax > 0.9 * vddh and vmin < 0.1 * vddh, "inverting": bool(inverting),
               "tplh": tplh, "tphl": tphl, "vmax": vmax, "vmin": vmin}
        r10 = wave.first_crossing(t, vo, 0.1 * vddh, "rise", T)
        r90 = wave.first_crossing(t, vo, 0.9 * vddh, "rise", r10) if not np.isnan(r10) else np.nan
        f90 = wave.first_crossing(t, vo, 0.9 * vddh, "fall", T)
        f10 = wave.first_crossing(t, vo, 0.1 * vddh, "fall", f90) if not np.isnan(f90) else np.nan
        res["trise"], res["tfall"] = r90 - r10, f10 - f90
        # duty cycle of output over the last full period
        rr = to_r[to_r > (ncyc - 2) * T]
        ff = to_f[to_f > (ncyc - 2) * T]
        if len(rr) and len(ff):
            if ff[0] > rr[0]:
                res["duty"] = float((ff[0] - rr[0]) / T)
            else:
                res["duty"] = float(1 - (rr[0] - ff[0]) / T)
    return res


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    sc = ctx.lib.get(a.dut)
    rd = run_dir(ctx)
    f0 = a.freq or c.FCLK
    ncyc = 4
    jobs, meta = [], []
    d, T = _deck(ctx, sc, c.VDD_LV, f0, a.cload, ncyc, "nominal")
    jobs.append((d, "nominal"))
    meta.append(("nom", c.VDD_LV, f0))
    vddls = [0.6, 0.7, 0.8, 0.9, 1.0, 1.08, 1.32] if not a.quick else [0.9, 1.08]
    for v in vddls:
        d, _ = _deck(ctx, sc, v, f0, a.cload, ncyc, f"vddl={v}")
        jobs.append((d, f"vddl_{v:.2f}"))
        meta.append(("vddl", v, f0))
    freqs = [100e6, 200e6, 400e6, 800e6, 1.6e9] if not a.quick else [200e6, 800e6]
    for f in freqs:
        d, _ = _deck(ctx, sc, c.VDD_LV, f, a.cload, ncyc, f"f={f}")
        jobs.append((d, f"f_{f / 1e6:.0f}MHz"))
        meta.append(("freq", c.VDD_LV, f))
    res = run_many(c, jobs, rd, "level shifter")

    nom = res[0].data()
    r0 = analyse(nom, 1 / f0, c.VDD_LV, c.VDD, ncyc)
    rep.add("functional @ nominal", int(r0.get("ok", False)), "", 1, "==")
    if not r0.get("ok"):
        rep.note("output does not swing rail-to-rail at nominal conditions")
    rep.add("inverting", int(r0.get("inverting", 0)))
    rep.add("tpLH (out rising)", r0.get("tplh"), "s", c.SPEC["ls_delay_max"], "<=",
            f"in 50% of {c.VDD_LV} V -> out 50% of {c.VDD} V, Cload={a.cload*1e15:.3g} fF")
    rep.add("tpHL (out falling)", r0.get("tphl"), "s", c.SPEC["ls_delay_max"], "<=")
    rep.add("rise time 10-90%", r0.get("trise"), "s")
    rep.add("fall time 90-10%", r0.get("tfall"), "s")
    rep.add("output duty cycle (in 50%)", 100 * r0.get("duty", np.nan), "%", (45, 55), "range")
    t = nom["t"]
    T0 = 1 / f0
    # static current: mid of high and low phases of the last period
    th = (ncyc - 1) * T0 + 0.25 * T0 + 0.2 * T0   # input high region
    tl = (ncyc - 1) * T0 + 0.75 * T0 + 0.2 * T0   # input low region (wraps ok)
    ih = abs(float(wave.value_at(t, nom["i(vvddh)"], min(th, t[-1]))))
    il = abs(float(wave.value_at(t, nom["i(vvddh)"], min(tl, t[-1]))))
    rep.add("static I(vddh), input high", ih, "A", 1e-6, "<=", "should be leakage only")
    rep.add("static I(vddh), input low", il, "A", 1e-6, "<=")
    e = -c.VDD * wave.integral(t, nom["i(vvddh)"], T0, 3 * T0) / 2 \
        - c.VDD_LV * wave.integral(t, nom["i(vvddl)"], T0, 3 * T0) / 2
    rep.add("energy per cycle", e, "J")

    ok_v = []
    for (kind, v, f), r in zip(meta, res):
        if kind == "vddl":
            rr = analyse(r.data(), 1 / f, v, c.VDD, ncyc)
            if rr.get("ok"):
                ok_v.append(v)
    rep.add("min working VDDL", min(ok_v) if ok_v else float("nan"), "V", 0.9 * c.VDD_LV, "<=",
            f"full-swing output at {f0/1e6:.3g} MHz")
    ok_f, fr = [], []
    for (kind, v, f), r in zip(meta, res):
        if kind == "freq":
            rr = analyse(r.data(), 1 / f, v, c.VDD, ncyc)
            fr.append((f, rr))
            if rr.get("ok"):
                ok_f.append(f)
    rep.add("max working frequency (tested)", max(ok_f) if ok_f else float("nan"), "Hz")

    # 3.3 -> 1.2 V buffer (comparator output into the 1.2 V FSM)
    from sartb.domains import ls_down_subckt, ls_pins
    dn = ls_down_subckt(c, ctx.lib)
    dp = ls_pins(dn, required=("vddl", "in", "out", "vss"))
    dd = deck(ctx, "down shifter")
    dd.use(dn.name)
    T0 = 1 / f0
    dd.add(f"Vvddl vddl 0 {c.VDD_LV}", "Vvss vss 0 0",
           f"Vin in 0 PULSE(0 {c.VDD} {fmt(T0 / 4)} 100p 100p {fmt(T0 / 2 - 100e-12)} {fmt(T0)})")
    roles = {dp[k]: n for k, n in (("vddl", "vddl"), ("in", "in"), ("out", "out"), ("vss", "vss"))}
    dd.add(instance_line("xdn", dn, roles), "Cl out 0 5f")
    dd.control(f"tran {fmt(T0 / 1000)} {fmt(ncyc * T0)}")
    dd.wrdata("o.txt", ["v(in)", "v(out)", "i(vvddl)"])
    (rdn,) = run_many(c, [(dd, "down")], rd, "down shifter")
    sd = rdn.data()
    rr = analyse(sd, T0, c.VDD, c.VDD_LV, ncyc)
    src = "your LS_DOWN_SUBCKT" if c.LS_DOWN_SUBCKT else "testbench-generated thick-oxide buffer"
    rep.add(f"down {c.VDD}->{c.VDD_LV} V: functional", int(rr.get("ok", False)), "", 1, "==", f"{dn.name} ({src})")
    rep.add("down: tpLH", rr.get("tplh"), "s", c.SPEC["ls_delay_max"], "<=")
    rep.add("down: tpHL", rr.get("tphl"), "s", c.SPEC["ls_delay_max"], "<=")
    tq = (ncyc - 1) * T0 + 0.45 * T0
    rep.add("down: static I(vddl), input high", abs(float(wave.value_at(sd["t"], sd["i(vvddl)"], tq))), "A",
            1e-6, "<=")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    m = (t > T0) & (t < 3 * T0)
    ax[0].plot(t[m] * 1e9, nom["v(in)"][m], label="in")
    ax[0].plot(t[m] * 1e9, nom["v(out)"][m], label="out")
    ax[0].set(xlabel="t [ns]", ylabel="V", title=f"{sc.name} @ {f0/1e6:.3g} MHz")
    ax[0].legend()
    ax[1].plot([f / 1e6 for f, _ in fr], [r.get("tplh", np.nan) * 1e12 for _, r in fr], "o-", label="tpLH")
    ax[1].plot([f / 1e6 for f, _ in fr], [r.get("tphl", np.nan) * 1e12 for _, r in fr], "s-", label="tpHL")
    ax[1].set(xscale="log", xlabel="f [MHz]", ylabel="delay [ps]", title="delay vs frequency")
    ax[1].legend()
    fig.tight_layout()
    rep.plot(fig, "level_shifter.png")
