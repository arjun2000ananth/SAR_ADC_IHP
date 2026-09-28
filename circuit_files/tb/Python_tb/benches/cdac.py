"""CDAC (cdac_caps_10b_diff + DAC switches + sampling tg): bit weights, attenuation, P/N match, major-carry settling, leakage, kT/C."""
from __future__ import annotations

import math

import numpy as np

from sartb import metrics, wave
from sartb.spice import fmt, pwl, run_deck

from .common import dac_window, deck, plt, run_dir, sampling_window
from .frontend import add_cdac, add_comparator, add_sampling, supplies


def add_args(p):
    p.add_argument("--tstep", type=float, default=None, help="time per DAC state (default 2 CLK)")
    p.add_argument("--tbit", type=float, default=None, help="settling time available per bit (default 1 CLK)")
    p.add_argument("--rref", type=float, default=0.0, help="reference source resistance [Ohm]")
    p.add_argument("--cref", type=float, default=0.0, help="decoupling cap on vrefp/vcm when --rref>0")
    p.add_argument("--no-comp", action="store_true", help="leave the comparator off the top plates")


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    n = c.NBITS
    rd = run_dir(ctx)
    t_s, src = sampling_window(c)
    tstep = a.tstep or 2 * c.TCLK
    tbit, tbit_src = (a.tbit, "--tbit") if a.tbit else dac_window(c)
    rep.note(f"settling budget {tbit*1e9:.3g} ns ({tbit_src})")
    ctot = c.CU * 2 ** n
    lsb = c.LSB
    vstep = c.VREFP - c.VCM

    #schedule
    t0 = 0.05e-6 + t_s + 20e-9                      # after sampling closes
    sched = []                                       # (time, {sel: value})
    state = {f"dbp{i}": 0 for i in range(n)} | {f"dbn{i}": 0 for i in range(n)}
    meas = []                                        # (label, t_before, t_after)
    t = t0
    for side in "pn":
        for i in range(n):
            meas.append((f"{side}{i}", t - 1e-12, t + tstep - 1e-12))
            sched.append((t, {f"db{side}{i}": 1}))
            t += tstep
            sched.append((t, {f"db{side}{i}": 0}))
            t += tstep
    # major carry on P side: 0111111111 - 1000000000
    sched.append((t, {f"dbp{i}": 1 for i in range(n - 1)}))
    t += tstep
    t_carry = t
    sched.append((t, {f"dbp{i}": 0 for i in range(n - 1)} | {f"dbp{n - 1}": 1}))
    t += 2 * tstep
    t_carry_back = t
    sched.append((t, {f"dbp{i}": 0 for i in range(n)}))
    t += tstep
    t_idle0 = t
    t_idle = 1e-6
    t_end = t + t_idle

    d = deck(ctx, "CDAC")
    if a.rref > 0:
        d.add(f"Vvdd vdd 0 {c.VDD}", "Vvss vss 0 0",
              f"Vvcm0 vcm0 0 {c.VCM}", f"Rcm vcm0 vcm {a.rref}",
              f"Vvref0 vref0 0 {c.VREFP}", f"Rref vref0 vrefp {a.rref}")
        if a.cref > 0:
            d.add(f"Ccm vcm 0 {a.cref}", f"Cref vrefp 0 {a.cref}")
    else:
        supplies(d, c)
    # small differential sample so the comparator never sees 0 V 
    # circuit with 0 V input is metastable and ngspice stops with "timestep too small")
    vd0 = 0.37 * lsb
    d.add(f"Vainp ainp 0 {c.VCM + vd0 / 2}", f"Vainn ainn 0 {c.VCM - vd0 / 2}")
    d.add(f"Vsample sample 0 PWL(0 0 50n 0 {fmt(50e-9 + c.T_EDGE)} {c.VDD} "
          f"{fmt(50e-9 + t_s)} {c.VDD} {fmt(50e-9 + t_s + c.T_EDGE)} 0)")
    for sel in state:
        pts = [(0.0, 0.0)]
        cur = 0
        for tt, ch in sched:
            if sel in ch and ch[sel] != cur:
                pts += [(tt, cur * c.VDD), (tt + c.T_EDGE, ch[sel] * c.VDD)]
                cur = ch[sel]
        d.add(f"V{sel} {sel} 0 {pwl(pts)}")
    add_sampling(d, ctx)
    add_cdac(d, ctx)
    if not a.no_comp:
        # comparator on the top plates, held in reset (CLK low): its input capacitance in the state
        # it has when a decision starts. Kickback is measured by the comparator / adc_timing benches.
        d.add("Vcompclk compclk 0 0")
        add_comparator(d, ctx, "compclk")
    d.control(f"tran {fmt(tbit / 200)} {fmt(t_end)} 0 {fmt(tbit / 100)}")
    vecs = ["v(vcp)", "v(vcn)", "v(bp9)", "v(bp8)", "v(vrefp)", "v(vcm)"]
    d.wrdata("cdac.txt", vecs)
    r = run_deck(c, d, rd, "cdac")
    s = r.data()
    tt = s["t"]
    vcp, vcn = s["v(vcp)"], s["v(vcn)"]
    rep.note(f"sampling window {t_s*1e9:.4g} ns ({src}); {tstep*1e9:.3g} ns per DAC state; Ctot/side={ctot*1e12:.4g} pF")

    # bit weights
    W = {"p": np.zeros(n), "n": np.zeros(n)}
    for label, tb, ta in meas:
        side, i = label[0], int(label[1:])
        node = vcp if side == "p" else vcn
        W[side][i] = wave.value_at(tt, node, ta) - wave.value_at(tt, node, tb)
    ideal = vstep * (2.0 ** np.arange(n)) * c.CU / ctot
    att = float(np.sum(W["p"]) / np.sum(ideal))
    cpar = ctot * (1 / att - 1)
    rep.add("top-plate attenuation (gain)", att, "x", desc="sum(measured)/sum(ideal) bit steps")
    rep.add("equivalent top-plate parasitic", cpar, "F",
            desc="Ctot*(1/att-1): tg junctions" + ("" if a.no_comp else " + comparator input"))
    rep.add("full-scale gain error from parasitic", (att - 1) * 100, "%",
            desc=f"= {(att - 1) * c.NCODES / 2:.2f} LSB at the ends of the range")
    werr = {sd: (W[sd] / att - ideal) / lsb for sd in "pn"}
    rep.add("max |bit weight error| (gain-normalised)", float(max(np.abs(werr["p"]).max(), np.abs(werr["n"]).max())),
            "LSB", c.SPEC["cdac_weight_err_lsb"], "<=")
    pn = (W["p"] - W["n"]) / lsb
    rep.add("max |P - N weight|", float(np.abs(pn).max()), "LSB", 0.25, "<=")
    rep.add("MSB step (P side)", float(W["p"][n - 1]), "V", desc=f"ideal {ideal[n - 1]:.4g} V")
    rep.add("unit step (P side)", float(W["p"][0]), "V", desc=f"ideal {ideal[0]*1e3:.4g} mV")
    rows = []
    for i in range(n):
        rows.append({"bit": i, "Wp": float(W["p"][i]), "Wn": float(W["n"][i]), "ideal": float(ideal[i]),
                     "err_p_lsb": float(werr["p"][i]), "err_n_lsb": float(werr["n"][i])})
    rep.data["weights"] = rows

    # major-carry settling
    final = wave.value_at(tt, vcp, t_carry_back - 1e-12)
    ts_carry = wave.settling_time(tt, vcp, t_carry, final, 0.5 * lsb, t_carry_back)
    glitch = float(np.max(np.abs(wave.window(tt, vcp, t_carry, t_carry + tbit)[1] - final)))
    rep.add("major-carry settling to 0.5LSB", ts_carry, "s", tbit, "<=",
            "P side 0111111111 -> 1000000000, all 10 switches toggle")
    rep.add("major-carry glitch (peak)", glitch, "V")
    msb_on = meas[n - 1]
    fin = wave.value_at(tt, vcp, msb_on[2])
    rep.add("MSB-only settling to 0.5LSB", wave.settling_time(tt, vcp, msb_on[1], fin, 0.5 * lsb, msb_on[2]), "s",
            tbit, "<=")

    # leakage drift of the floating top plates
    v0 = wave.value_at(tt, vcp - vcn, t_idle0 + 50e-9)
    v1 = wave.value_at(tt, vcp - vcn, t_end - 1e-12)
    drift = (v1 - v0) / (t_end - t_idle0 - 50e-9)
    rep.add("hold drift (diff)", drift * 1e-6 / lsb, "LSB", desc="per microsecond, top plates floating")
    tconv = 1 / c.FS_TARGET
    rep.add("hold drift over one conversion", abs(drift) * tconv / lsb, "LSB", 0.1, "<=")

    # kT/C
    ceff = ctot + cpar
    sig_n = math.sqrt(2 * metrics.kT_over_C(ceff, c.TEMP))
    rep.add("kT/C noise (diff, rms)", sig_n, "V")
    rep.add("kT/C noise (diff, rms)", sig_n / lsb, "LSB")
    ps = (c.VFS / 2) ** 2 / 2
    snr_ktc = 10 * math.log10(ps / sig_n ** 2)
    rep.add("SNR limit from kT/C (FS sine)", snr_ktc, "dB")
    q = lsb ** 2 / 12
    rep.add("SNR limit kT/C + quantisation", 10 * math.log10(ps / (sig_n ** 2 + q)), "dB")

    # plots 
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    ax[0, 0].bar(np.arange(n) - 0.2, werr["p"], 0.4, label="P")
    ax[0, 0].bar(np.arange(n) + 0.2, werr["n"], 0.4, label="N")
    ax[0, 0].set(xlabel="bit", ylabel="weight error [LSB]", title=f"bit weights (gain {att:.4f} removed)")
    ax[0, 0].legend()
    ax[0, 1].plot(tt * 1e9, vcp, label="vcp")
    ax[0, 1].plot(tt * 1e9, vcn, label="vcn")
    ax[0, 1].set(xlabel="t [ns]", ylabel="V", title="top plates over the whole sequence")
    ax[0, 1].legend()
    m = (tt > t_carry - 2e-9) & (tt < t_carry + 1.5 * tbit)
    ax[1, 0].plot((tt[m] - t_carry) * 1e9, (vcp[m] - final) / lsb)
    ax[1, 0].axhline(0.5, ls=":", c="r")
    ax[1, 0].axhline(-0.5, ls=":", c="r")
    ax[1, 0].set_ylim(-10, 10)
    ax[1, 0].set(xlabel="t [ns]", ylabel="vcp - final [LSB]", title="major-carry settling")
    ax[1, 1].plot((tt[m] - t_carry) * 1e9, s["v(bp9)"][m], label="bp9")
    ax[1, 1].plot((tt[m] - t_carry) * 1e9, s["v(bp8)"][m], label="bp8")
    ax[1, 1].plot((tt[m] - t_carry) * 1e9, s["v(vrefp)"][m], label="vrefp")
    ax[1, 1].set(xlabel="t [ns]", ylabel="V", title="bottom plates during carry")
    ax[1, 1].legend()
    fig.tight_layout()
    rep.plot(fig, "cdac.png")
