"""capDrivers """
from __future__ import annotations

import numpy as np

from sartb import wave
from sartb.spice import fmt, pwl, run_deck

from .common import dac_window, deck, instance_line, plt, run_dir


def add_args(p):
    p.add_argument("--dut", default="capDrivers")
    p.add_argument("--cu", type=float, default=None, help="unit cap of the array this drives (default CU)")
    p.add_argument("--tstep", type=float, default=None, help="time per state (default 2 CLK)")
    p.add_argument("--tbit", type=float, default=None, help="settling budget (default 1 CLK)")


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    sc = ctx.lib.get(a.dut)
    rd = run_dir(ctx)
    n = c.NBITS
    cu = a.cu or c.CU
    vdd = c.VDD_LV
    tstep = a.tstep or 2 * c.TCLK
    tbit, tbit_src = (a.tbit, "--tbit") if a.tbit else dac_window(c)
    rep.note(f"settling budget {tbit*1e9:.3g} ns ({tbit_src})")
    ctot = cu * 2 ** n
    lsb = vdd / 2 ** n                     # single-ended top-plate LSB of a 1.2 V-referenced array
    nets = {"VDD": "vdd", "VSS": "vss"}
    for i in range(n):
        nets[f"In{i}"] = f"in{i}"
        nets[f"Drv{i}"] = f"b{i}"

    # schedule: each bit alone up/down, then major carry
    t0 = 60e-9
    sched = []
    t = t0
    per_bit = []
    for i in range(n):
        per_bit.append((i, t, t + tstep))
        sched.append((t, {i: 1}))
        t += tstep
        sched.append((t, {i: 0}))
        t += tstep
    sched.append((t, {i: 1 for i in range(n - 1)}))
    t += tstep
    t_carry = t
    sched.append((t, {i: 0 for i in range(n - 1)} | {n - 1: 1}))
    t += 2 * tstep
    t_end = t

    d = deck(ctx, "capDrivers")
    d.use(sc.name)
    d.add(f"Vvdd vdd 0 {vdd}", "Vvss vss 0 0", f"Vtop topsrc 0 {vdd / 2}",
          "Vrel rel 0 PWL(0 1 40n 1 40.05n 0)", "Srel topsrc top rel 0 swrel",
          ".model swrel sw vt=0.5 vh=0.1 ron=10 roff=1e14")
    d.add(instance_line("xdut", sc, nets))
    for i in range(n):
        pts = [(0.0, 0.0)]
        cur = 0
        for tt, ch in sched:
            if i in ch and ch[i] != cur:
                pts += [(tt, cur * vdd), (tt + 50e-12, ch[i] * vdd)]
                cur = ch[i]
        d.add(f"Vin{i} in{i} 0 {pwl(pts)}", f"Cb{i} b{i} top {cu * 2 ** i}")
    d.add(f"Cdummy top 0 {cu}")
    d.control(f"tran {fmt(tbit / 400)} {fmt(t_end)} 0 {fmt(tbit / 200)}")
    vecs = ["v(top)"] + [f"v(b{i})" for i in range(n)] + ["i(vvdd)"]
    d.wrdata("cd.txt", vecs)
    r = run_deck(c, d, rd, "capdrivers")
    s = r.data()
    tt = s["t"]
    top = s["v(top)"]

    rows = []
    for i, ton, toff in per_bit:
        b = s[f"v(b{i})"]
        # In high -> Drv low (inverter): falling bottom plate first
        f90 = wave.first_crossing(tt, b, 0.9 * vdd, "fall", ton)
        f10 = wave.first_crossing(tt, b, 0.1 * vdd, "fall", ton)
        r10 = wave.first_crossing(tt, b, 0.1 * vdd, "rise", toff)
        r90 = wave.first_crossing(tt, b, 0.9 * vdd, "rise", toff)
        fin1 = wave.value_at(tt, top, toff - 1e-12)
        fin2 = wave.value_at(tt, top, toff + tstep - 1e-12)
        s1 = wave.settling_time(tt, top, ton, fin1, 0.5 * lsb, toff)
        s2 = wave.settling_time(tt, top, toff, fin2, 0.5 * lsb, toff + tstep)
        rows.append({"bit": i, "tfall": f10 - f90, "trise": r90 - r10, "settle_dn": s1, "settle_up": s2,
                     "step": float(wave.value_at(tt, top, ton - 1e-12) - fin1)})
    for rr in rows[::-1][:3]:
        rep.add(f"bit {rr['bit']} bottom fall / rise", rr["tfall"], "s", desc=f"rise {rr['trise']*1e12:.0f} ps")
        rep.add(f"bit {rr['bit']} top settle to 0.5LSB", max(rr["settle_dn"], rr["settle_up"]), "s")
    worst = max(max(r_["settle_dn"], r_["settle_up"]) for r_ in rows)
    rep.add("worst per-bit settling", worst, "s", tbit, "<=",
            f"0.5 LSB = {0.5*lsb*1e3:.3g} mV on the top plate (Cu={cu*1e15:.3g} fF, {vdd} V ref)")
    steps = np.array([r_["step"] for r_ in rows])
    ideal = vdd * cu * 2.0 ** np.arange(n) / (ctot + cu)
    g = steps.sum() / ideal.sum()
    rep.add("max |step error| (gain-normalised)", float(np.max(np.abs(steps / g - ideal)) / lsb), "LSB", 0.25, "<=")
    fin = wave.value_at(tt, top, t_end - 1e-12)
    sc_ = wave.settling_time(tt, top, t_carry, fin, 0.5 * lsb, t_end)
    rep.add("major-carry settling", sc_, "s", tbit, "<=", "In 0111111111 -> 1000000000")
    e = -vdd * wave.integral(tt, s["i(vvdd)"], t0, per_bit[-1][2] + tstep)
    rep.add("energy, each bit toggled once up+down", e, "J")
    rep.data["bits"] = rows

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].semilogy([r_["bit"] for r_ in rows], [r_["tfall"] * 1e12 for r_ in rows], "o-", label="bottom fall")
    ax[0].semilogy([r_["bit"] for r_ in rows], [r_["trise"] * 1e12 for r_ in rows], "s-", label="bottom rise")
    ax[0].semilogy([r_["bit"] for r_ in rows], [max(r_["settle_dn"], r_["settle_up"]) * 1e12 for r_ in rows],
                   "^-", label="top settle 0.5LSB")
    ax[0].axhline(tbit * 1e12, ls=":", c="r")
    ax[0].set(xlabel="bit", ylabel="ps", title="per-bit timing")
    ax[0].legend()
    m = (tt > t_carry - 2e-9) & (tt < t_carry + tbit)
    ax[1].plot((tt[m] - t_carry) * 1e9, (top[m] - fin) / lsb)
    ax[1].axhline(0.5, ls=":", c="r")
    ax[1].axhline(-0.5, ls=":", c="r")
    ax[1].set_ylim(-20, 20)
    ax[1].set(xlabel="t [ns]", ylabel="top - final [LSB]", title="major carry")
    fig.tight_layout()
    rep.plot(fig, "cap_drivers.png")
