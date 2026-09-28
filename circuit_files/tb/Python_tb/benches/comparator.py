"""Clocked comparator: offset & hysteresis, CM sweep, delay/regeneration tau, kickback, power, MC offset."""
from __future__ import annotations

import math

import numpy as np

from sartb import wave
from sartb.spice import fmt, pwl, run_many

from .common import deck, instance_line, map_pins, plt, run_dir


def add_args(p):
    p.add_argument("--dut", default="strong_arm_comp", help="comparator subckt (strong_arm_comp, simple_comparator)")
    p.add_argument("--pins", default=None, help="role=Port overrides, e.g. outp=Voutp,clk=CLK")
    p.add_argument("--tclk", type=float, default=None, help="comparator clock period (default 1/FCLK)")
    p.add_argument("--cload", type=float, default=10e-15, help="load cap on each output")
    p.add_argument("--cms", default=None, help="comma list of input common-mode voltages")
    p.add_argument("--ramp-lsb", type=float, default=4.0, help="offset ramp span (+/- LSB)")
    p.add_argument("--ramp-steps", type=int, default=160, help="ramp steps per direction")
    p.add_argument("--mc", type=int, default=0, help="mismatch Monte Carlo runs for offset sigma")


ROLES = ["inp", "inn", "outp", "outn", "clk", "vdd", "vss"]


# deck
def _input_pwl(vals, T, base, sign, t_change=0.1, t_edge=50e-12):
    pts = [(0.0, base + sign * vals[0] / 2)]
    for k in range(1, len(vals)):
        t = k * T + t_change * T
        pts.append((t, base + sign * vals[k - 1] / 2))
        pts.append((t + t_edge, base + sign * vals[k] / 2))
    return pwl(pts)


def make_deck(ctx, sc, pins, T, vids, cm, cload, title, mismatch=False, seed=None,
              kick=False, t_open=None, tmax_div=400, eval_cycles=None):
    c = ctx.cfg
    d = deck(ctx, title, mismatch=mismatch)
    d.use(sc.name)
    if seed is not None:
        d.pre.append(f"pre_set rndseed={seed}")
    nets = {pins["inp"]: "inp", pins["inn"]: "inn", pins["outp"]: "outp", pins["outn"]: "outn",
            pins["clk"]: "clk", pins["vdd"]: "vdd", pins["vss"]: "vss"}
    d.add(instance_line("xdut", sc, nets))
    d.add(f"Vvdd vdd 0 {c.VDD}", "Vvss vss 0 0")
    if eval_cycles is None:
        d.add(f"Vclk clk 0 PULSE(0 {c.VDD} {fmt(T / 2)} {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} "
              f"{fmt(T / 2 - c.T_EDGE)} {fmt(T)})")
    else:   # evaluate only in the listed cycles (clock held low = reset otherwise)
        pts = [(0.0, 0.0)]
        for k in eval_cycles:
            pts += [((k + 0.5) * T, 0.0), ((k + 0.5) * T + c.T_EDGE, c.VDD),
                    ((k + 1) * T - c.T_EDGE, c.VDD), ((k + 1) * T, 0.0)]
        d.add(f"Vclk clk 0 {pwl(pts)}")
    d.add(f"Cloadp outp 0 {cload}", f"Cloadn outn 0 {cload}")
    if not kick:
        d.add(f"Vinp inp 0 {_input_pwl(vids, T, cm, +1)}", f"Vinn inn 0 {_input_pwl(vids, T, cm, -1)}")
    else:
        ctop = c.CU * 2 ** c.NBITS
        d.add(f"Vinp inp_s 0 {_input_pwl(vids, T, cm, +1)}", f"Vinn inn_s 0 {_input_pwl(vids, T, cm, -1)}")
        d.add(f"Vtrk trk 0 PWL(0 1 {fmt(t_open)} 1 {fmt(t_open + 50e-12)} 0)")
        d.add("Strkp inp_s inp trk 0 swtrk", "Strkn inn_s inn trk 0 swtrk",
              ".model swtrk sw vt=0.5 vh=0.1 ron=10 roff=1e14")
        if kick == "cdac":
            # the real input network: CDAC caps whose bottom plates sit on vcm through the DAC switches
            from .frontend import add_cdac
            d.add(f"Vvcm vcm 0 {c.VCM}", f"Vvref vrefp 0 {c.VREFP}", "Vzero zero 0 0")
            add_cdac(d, ctx, top_p="inp", top_n="inn", sel_p=lambda i: "zero", sel_n=lambda i: "zero")
        else:
            d.add(f"Ctopp inp 0 {ctop}", f"Ctopn inn 0 {ctop}")
    tstop = len(vids) * T
    d.control(f"tran {fmt(T / tmax_div)} {fmt(tstop)}")
    d.wrdata("out.txt", ["v(inp)", "v(inn)", "v(outp)", "v(outn)", "v(clk)", "i(vvdd)"])
    return d


# analysis
def decisions(dat, T, n, vdd):
    t = dat["t"]
    tq = (np.arange(n) + 0.97) * T
    op = wave.value_at(t, dat["v(outp)"], tq)
    on = wave.value_at(t, dat["v(outn)"], tq)
    return (op > on).astype(int), op - on


def ramp_vids(center, half_span, n):
    """2 large preset cycles, then a staircase up and back down (one step per clock)."""
    up = center + np.linspace(-half_span, half_span, n)
    return np.concatenate([[-0.2, 0.2], up, up[::-1]])


def analyse_ramp(dat, vids, T, vdd):
    n = len(vids)
    dec, _ = decisions(dat, T, n, vdd)
    nr = (n - 2) // 2
    up_v, up_d = vids[2:2 + nr], dec[2:2 + nr]
    dn_v, dn_d = vids[2 + nr:], dec[2 + nr:]
    pol = 1 if dec[1] == 1 else -1         
    if pol < 0:
        up_d, dn_d = 1 - up_d, 1 - dn_d

    def trip(v, d, rising):
        # last index before the final switch
        target = 1 if rising else 0
        idx = np.nonzero(d != target)[0]
        if len(idx) == 0 or idx[-1] == len(d) - 1:
            return float("nan")
        i = idx[-1]
        return 0.5 * (v[i] + v[i + 1])

    vt_up = trip(up_v, up_d, True)
    vt_dn = trip(dn_v, dn_d, False)
    flips = int(np.sum(np.abs(np.diff(up_d)))) + int(np.sum(np.abs(np.diff(dn_d))))
    return {"pol": pol, "vt_up": vt_up, "vt_dn": vt_dn,
            "offset": 0.5 * (vt_up + vt_dn), "hyst": vt_up - vt_dn, "flips": flips}


def analyse_delay(dat, tests, T, vdd, pol):
    """tests: list of (cycle index, sign, overdrive). Returns list of delays (nan = wrong/none)."""
    t = dat["t"]
    diff = dat["v(outp)"] - dat["v(outn)"]
    out = []
    for k, s, vod in tests:
        t_clk = k * T + T / 2
        y = pol * s * diff
        tc = wave.first_crossing(t, y, 0.5 * vdd, "rise", t_clk, (k + 1) * T)
        final = wave.value_at(t, y, (k + 0.97) * T)
        out.append(tc - t_clk if (not math.isnan(tc) and final > 0) else float("nan"))
    return np.array(out)


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    sc = ctx.lib.get(a.dut)
    pins = map_pins(sc, ROLES, a.pins)
    T = a.tclk or c.TCLK
    lsb = c.LSB
    rep.data["pins"] = pins
    rep.note(f"DUT {sc.name}: pins {pins}; comparator clock {T*1e9:.3g} ns "
             f"(reset while CLK low, evaluate while CLK high); Cload={a.cload*1e15:.3g} fF")
    if a.cms:
        cms = [float(x) for x in a.cms.split(",")]
    else:
        cms = list(np.round(np.linspace(0.5, c.VDD - 0.3, 3 if a.quick else 8), 3))
        if c.VCM not in cms:
            cms.append(c.VCM)
        cms = sorted(cms)
    rd = run_dir(ctx)

    # offset / hysteresis vs CM: coarse ramp, then fine ramp
    n_coarse = 40 if a.quick else a.ramp_steps
    vids = ramp_vids(0.0, a.ramp_lsb * lsb, n_coarse)
    jobs = [(make_deck(ctx, sc, pins, T, vids, cm, a.cload, f"ramp cm={cm}", tmax_div=200),
             f"ramp_cm{cm:.3f}") for cm in cms]
    res = run_many(c, jobs, rd, "offset coarse")
    coarse = {cm: analyse_ramp(r.data(), vids, T, c.VDD) for cm, r in zip(cms, res)}
    cstep = {cm: vids[3] - vids[2] for cm in cms}
    # trip point outside the ramp (e.g. at the edge of the CM range): retry with a 32x wider ramp
    wide = [cm for cm in cms if math.isnan(coarse[cm]["offset"])]
    if wide:
        wv = ramp_vids(0.0, 32 * a.ramp_lsb * lsb, n_coarse)
        wres = run_many(c, [(make_deck(ctx, sc, pins, T, wv, cm, a.cload, f"wide cm={cm}", tmax_div=200),
                             f"wide_cm{cm:.3f}") for cm in wide], rd, "offset wide")
        for cm, r in zip(wide, wres):
            coarse[cm] = analyse_ramp(r.data(), wv, T, c.VDD)
            cstep[cm] = wv[3] - wv[2]
    fine_vids = {}
    fjobs = []
    for cm in cms:
        step = cstep[cm]
        ctr = coarse[cm]["offset"]
        ctr = 0.0 if math.isnan(ctr) else ctr
        fv = ramp_vids(ctr, 1.5 * step + abs(coarse[cm]["hyst"] if not math.isnan(coarse[cm]["hyst"]) else 0),
                       20 if a.quick else 40)
        fine_vids[cm] = fv
        fjobs.append((make_deck(ctx, sc, pins, T, fv, cm, a.cload, f"fine cm={cm}", tmax_div=200),
                      f"fine_cm{cm:.3f}"))
    fres = run_many(c, fjobs, rd, "offset fine")
    ramps = {}
    for cm, r in zip(cms, fres):
        fr = analyse_ramp(r.data(), fine_vids[cm], T, c.VDD)
        ramps[cm] = fr if not math.isnan(fr["offset"]) else coarse[cm]
        ramps[cm]["resolution"] = float(fine_vids[cm][3] - fine_vids[cm][2]) \
            if not math.isnan(fr["offset"]) else float(cstep[cm])
    bad_cm = [cm for cm in cms if math.isnan(ramps[cm]["offset"])]
    if bad_cm:
        rep.note(f"no trip point within +/-{32 * a.ramp_lsb:.0f} LSB at CM = {bad_cm} V "
                 f"(comparator not working there)")
    r0 = ramps[c.VCM]
    pol = r0["pol"]
    if pol < 0:
        rep.note("polarity: output 'outp' goes HIGH when Vinp < Vinn (inverted w.r.t. port names)")
    rep.add("polarity (+1: outp high for Vinp>Vinn)", pol)
    rep.add("offset @VCM", r0["offset"], "V", c.SPEC["comp_offset_lsb"] * lsb, "abs<=",
            "systematic input-referred offset (ramp up/down average)")
    rep.add("offset @VCM", r0["offset"] / lsb, "LSB")
    rep.add("hysteresis @VCM", r0["hyst"], "V", 0.25 * lsb, "abs<=",
            "trip(up) - trip(down); memory from incomplete reset")
    rep.add("offset resolution", ramps[c.VCM]["resolution"], "V")
    if r0["flips"] > 2:
        rep.note(f"decision chattered {r0['flips']} times across the ramp (noise/metastability?)")

    # delay vs overdrive at each CM
    vods = np.array([1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 0.5 * lsb, lsb, 1e-2, 3e-2, 1e-1])
    if a.quick:
        vods = np.array([1e-4, 1e-3, 0.5 * lsb, lsb, 1e-2])
    djobs, dmeta = [], []
    for cm in cms:
        off = ramps[cm]["offset"] if not math.isnan(ramps[cm]["offset"]) else 0.0
        seq, tests = [], []
        for s in (+1, -1):
            for v in vods:
                seq.append(off - s * 0.2)          # preset opposite state
                seq.append(off + s * v)
                tests.append((len(seq) - 1, s, v))
        djobs.append((make_deck(ctx, sc, pins, T, np.array(seq), cm, a.cload, f"delay cm={cm}",
                                tmax_div=1000), f"delay_cm{cm:.3f}"))
        dmeta.append((cm, tests))
    dres = run_many(c, djobs, rd, "delay")
    delay = {}
    for (cm, tests), r in zip(dmeta, dres):
        dl = analyse_delay(r.data(), tests, T, c.VDD, pol)
        n = len(vods)
        delay[cm] = {"pos": dl[:n], "neg": dl[n:]}
    d0 = delay[c.VCM]
    worst = np.fmax(d0["pos"], d0["neg"])
    i_half = int(np.argmin(np.abs(vods - 0.5 * lsb)))
    i_one = int(np.argmin(np.abs(vods - lsb)))
    rep.add("delay @0.5LSB overdrive", worst[i_half], "s", c.SPEC["comp_delay_max"], "<=",
            "CLK rise -> |outp-outn| > VDD/2, worst polarity")
    rep.add("delay @1LSB overdrive", worst[i_one], "s")
    rep.add("delay @100mV overdrive", worst[-1], "s")
    # regeneration tau from the small-signal part
    small = (vods <= 1e-3) & ~np.isnan(worst)
    tau = float("nan")
    if small.sum() >= 3:
        slope, _ = np.polyfit(np.log(vods[small]), worst[small], 1)
        tau = -slope
    rep.add("regeneration tau", tau, "s", desc="d(delay)/d ln(1/Vod)")
    t_avail = T / 2
    unresolved = [v for v, dl in zip(vods, worst) if math.isnan(dl) or dl > t_avail]
    rep.add("smallest overdrive resolved in T/2", float(min([v for v, dl in zip(vods, worst)
                                                             if not math.isnan(dl) and dl <= t_avail],
                                                            default=float("nan"))), "V")
    if unresolved:
        rep.note(f"overdrives not resolved within T/2={t_avail*1e9:.3g} ns: "
                 + ", ".join(f"{v*1e6:.3g}uV" for v in unresolved))

    # CM range
    ok_cm = [cm for cm in cms
             if not math.isnan(ramps[cm]["offset"])
             and abs(ramps[cm]["offset"]) <= c.SPEC["comp_offset_lsb"] * lsb
             and not math.isnan(np.fmax(delay[cm]["pos"], delay[cm]["neg"])[i_one])
             and np.fmax(delay[cm]["pos"], delay[cm]["neg"])[i_one] <= c.SPEC["comp_delay_max"]]
    rep.add("CM range OK (min)", min(ok_cm) if ok_cm else float("nan"), "V")
    rep.add("CM range OK (max)", max(ok_cm) if ok_cm else float("nan"), "V")

    # power and output levels (from the VCM ramp run)
    dat = res[cms.index(c.VCM)].data()
    t = dat["t"]
    t0, t1 = 2 * T, len(vids) * T
    p_avg = -c.VDD * wave.average(t, dat["i(vvdd)"], t0, t1)
    rep.add("power @fclk", p_avg, "W")
    rep.add("energy / comparison", p_avg * T, "J")
    hold = np.zeros_like(t, bool)
    for k in range(2, len(vids)):
        hold |= (t > k * T + 0.2 * T) & (t < k * T + 0.48 * T)
    lo = float(min(dat["v(outp)"][hold].min(), dat["v(outn)"][hold].min()))
    hi = float(max(dat["v(outp)"][hold].max(), dat["v(outn)"][hold].max()))
    rep.add("output min during reset phase", lo, "V", (-0.1, c.VDD + 0.1), "warn-range",
            "floating/dynamic output nodes show up here")
    rep.add("output max during reset phase", hi, "V", (-0.1, c.VDD + 0.1), "warn-range")
    if lo < -0.1:
        rep.note(f"an output node is driven to {lo:.3f} V during reset -> that node is floating "
                 f"(no keeper) and is capacitively kicked below ground by CLK")

    # Kickback onto the floating CDAC top plates
    kmode = "cdac" if (ctx.lib.has("cdac_caps_10b_diff") and ctx.lib.has("dac_sw_2to1_tg")) else "caps"
    cases = [(p, s) for p in (+1, -1) for s in (+1, -1)]
    kjobs = []
    K = 8          # settle for K-1 clock periods (comparator in reset) after the preset decision
    for p, s in cases:
        seq = np.array([p * 0.2] + [s * 0.5 * lsb] * (K + 2))
        kjobs.append((make_deck(ctx, sc, pins, T, seq, c.VCM, a.cload, f"kick p={p} s={s}", kick=kmode,
                                t_open=(K + 0.35) * T, tmax_div=2000, eval_cycles=[0, K, K + 1]),
                      f"kick_{'p' if p > 0 else 'n'}{'p' if s > 0 else 'n'}"))
    kres = run_many(c, kjobs, rd, "kickback")
    kb, wrong = [], 0
    for (p, s), r in zip(cases, kres):
        dk = r.data()
        tt = dk["t"]
        vd = dk["v(inp)"] - dk["v(inn)"]
        vc = 0.5 * (dk["v(inp)"] + dk["v(inn)"])
        t_edge = (K + 0.5) * T
        base_d, base_c = wave.value_at(tt, vd, t_edge - 0.2e-9), wave.value_at(tt, vc, t_edge - 0.2e-9)
        m = (tt > t_edge) & (tt < t_edge + 1e-9)
        peak = float(np.max(np.abs(vd[m] - base_d)))
        at_dec = float(wave.value_at(tt, vd, t_edge + 0.3e-9) - base_d)
        net = float(wave.value_at(tt, vd, (K + 1.45) * T) - base_d)
        cm_net = float(wave.value_at(tt, vc, (K + 1.45) * T) - base_c)
        dec, _ = decisions(dk, T, K + 1, c.VDD)
        ok = (dec[K] == 1) == ((s * pol) > 0)
        wrong += int(not ok)
        kb.append({"preset": p, "sign": s, "peak": peak, "at_decision": at_dec, "net": net, "cm_net": cm_net,
                   "correct": bool(ok)})
    net_desc = "real CDAC + DAC switches" if kmode == "cdac" else f"{c.CU * 2 ** c.NBITS * 1e12:.3g} pF ideal caps"
    rep.add("kickback diff at decision (+0.3 ns)", max(abs(k["at_decision"]) for k in kb) / lsb, "LSB", 0.25,
            "<=", f"input network: {net_desc}; the comparator decides on input + this kick")
    rep.add("kickback diff, peak in first 1 ns", max(k["peak"] for k in kb) / lsb, "LSB")
    rep.add("kickback diff, net per cycle", max(abs(k["net"]) for k in kb) / lsb, "LSB", 0.1, "<=")
    rep.add("kickback common-mode, net", max(abs(k["cm_net"]) for k in kb), "V")
    rep.add("wrong decisions at +/-0.5 LSB (floating inputs)", wrong, "", 0, "<=",
            "4 cases: previous decision same/opposite x input sign")

    #Monte-Carlo offset
    if a.mc > 0:
        mv = ramp_vids(0.0, a.ramp_lsb * lsb, n_coarse)
        mjobs = [(make_deck(ctx, sc, pins, T, mv, c.VCM, a.cload, f"mc {i}", tmax_div=200,
                            mismatch=True, seed=i + 1), f"mc_{i:03d}") for i in range(a.mc)]
        mres = run_many(c, mjobs, rd, "MC")
        offs = []
        for r in mres:
            rr = analyse_ramp(r.data(), mv, T, c.VDD)
            offs.append(rr["offset"])
        offs = np.array(offs)
        nan_n = int(np.isnan(offs).sum())
        if nan_n:
            rep.note(f"{nan_n} MC samples had offset outside the +/-{a.ramp_lsb} LSB ramp "
                     f"-> increase --ramp-lsb")
        o = offs[~np.isnan(offs)]
        rep.add("MC offset mean", float(np.mean(o)) if len(o) else float("nan"), "V")
        rep.add("MC offset sigma", float(np.std(o, ddof=1)) if len(o) > 1 else float("nan"), "V",
                c.SPEC["comp_mc_sigma_lsb"] * lsb, "<=", f"{len(o)} samples")
        rep.add("MC offset sigma", float(np.std(o, ddof=1)) / lsb if len(o) > 1 else float("nan"), "LSB")
        rep.data["mc_offsets"] = offs.tolist()

    rep.data.update({"cms": cms, "ramps": ramps, "vods": vods.tolist(),
                     "delay": {str(k): {kk: vv.tolist() for kk, vv in v.items()} for k, v in delay.items()},
                     "kickback": kb})

    # plots
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    dec, _ = decisions(dat, T, len(vids), c.VDD)
    nr = (len(vids) - 2) // 2
    decp = dec if pol > 0 else 1 - dec
    ax[0, 0].step(vids[2:2 + nr] / lsb, decp[2:2 + nr], where="mid", label="ramp up")
    ax[0, 0].step(vids[2 + nr:] / lsb, decp[2 + nr:] + 0.03, where="mid", label="ramp down")
    ax[0, 0].set(xlabel="Vid [LSB]", ylabel="decision", title=f"transfer @ Vcm={c.VCM} V")
    ax[0, 0].legend()
    ax[0, 1].plot(cms, [ramps[cm]["offset"] / lsb for cm in cms], "o-", label="offset")
    ax[0, 1].plot(cms, [ramps[cm]["hyst"] / lsb for cm in cms], "s--", label="hysteresis")
    ax[0, 1].set(xlabel="input CM [V]", ylabel="LSB", title="offset vs common mode")
    ax[0, 1].legend()
    for cm in cms:
        w = np.fmax(delay[cm]["pos"], delay[cm]["neg"])
        ax[1, 0].semilogx(vods, w * 1e9, "o-", label=f"{cm:.2f} V", ms=3)
    ax[1, 0].axvline(lsb, ls=":", c="k")
    ax[1, 0].axhline(T / 2 * 1e9, ls=":", c="r")
    ax[1, 0].set(xlabel="overdrive [V]", ylabel="delay [ns]", title="decision delay (worst polarity)")
    ax[1, 0].legend(fontsize=7, ncol=2)
    k = 3
    m = (t > (k - 0.1) * T) & (t < (k + 1.2) * T)
    ax[1, 1].plot(t[m] * 1e9, dat["v(clk)"][m], label="clk")
    ax[1, 1].plot(t[m] * 1e9, dat["v(outp)"][m], label="outp")
    ax[1, 1].plot(t[m] * 1e9, dat["v(outn)"][m], label="outn")
    ax[1, 1].set(xlabel="t [ns]", ylabel="V", title="waveforms (ramp run)")
    ax[1, 1].legend()
    fig.suptitle(f"{sc.name}  {c.CORNER} {c.TEMP}C VDD={c.VDD}")
    fig.tight_layout()
    rep.plot(fig, "comparator.png")
    if a.mc > 0 and len(o) > 2:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(o / lsb, bins=max(8, len(o) // 4))
        ax.set(xlabel="offset [LSB]", ylabel="count", title=f"MC offset, sigma={np.std(o, ddof=1)/lsb:.3f} LSB")
        rep.plot(fig, "comparator_mc.png")
