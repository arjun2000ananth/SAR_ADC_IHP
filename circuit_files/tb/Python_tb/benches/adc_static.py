"""ADC static linearity: DNL/INL, missing codes, offset & gain error (bit-weight, histogram or transition search)."""
from __future__ import annotations

import numpy as np

from sartb import metrics
from sartb.adc import AdcEngine, cdac_mismatch_text

from .common import ensure_timing, plt, run_dir


def add_args(p):
    p.add_argument("--method", choices=["bitweights", "hist", "transitions"], default="bitweights",
                   help="bitweights: bisection on ~40 major-carry transitions + SAR weight model (fast); "
                        "hist: DC staircase histogram over all codes (slow, model-free); "
                        "transitions: bisection on --codes (default all 1023; slowest, most precise)")
    p.add_argument("--hits", type=int, default=4, help="hist: conversions per code")
    p.add_argument("--rounds", type=int, default=7, help="bisection rounds (resolution = 4 LSB / 2^rounds)")
    p.add_argument("--codes", default="all", help="transitions: 'all' or comma list")
    p.add_argument("--variant", choices=["real", "ideal"], default="real")
    p.add_argument("--fsm-model", choices=["xspice", "spice"], default=None)
    p.add_argument("--ls-model", choices=["xspice", "spice"], default=None,
                   help="level shifters: in the XSPICE bridges (fast) or transistor level")
    p.add_argument("--cap-mismatch", type=float, default=0.0,
                   help="relative sigma of one unit cap (e.g. 0.002); adds random CDAC mismatch")
    p.add_argument("--seed", type=int, default=1)


def search_transitions(eng, ks, rounds, rd, c, label):
    lsb = c.LSB
    pts: list[tuple[float, int]] = []

    def brackets():
        arr = sorted(pts)
        v = np.array([p[0] for p in arr])
        cd = np.array([p[1] for p in arr])
        out = {}
        for k in ks:
            below = np.nonzero((cd < k) & (cd >= 0))[0]
            lo = v[below[-1]] if len(below) else None
            above = np.nonzero((cd >= k) & (v > (lo if lo is not None else -np.inf)))[0]
            hi = v[above[0]] if len(above) else None
            out[k] = (lo, hi)
        return out

    ideal = {k: -c.VFS / 2 + k * lsb for k in ks}
    span = 2 * lsb
    todo = sorted({round(ideal[k] - span, 9) for k in ks} | {round(ideal[k] + span, 9) for k in ks})
    for it in range(4):
        codes = eng.convert(todo, f"{label}_b{it}", rd)
        pts.extend(zip(todo, codes.tolist()))
        br = brackets()
        todo = []
        for k, (lo, hi) in br.items():
            if lo is None:
                todo.append(ideal[k] - span * 2 ** (it + 2))
            if hi is None:
                todo.append(ideal[k] + span * 2 ** (it + 2))
        todo = sorted(set(round(x, 9) for x in todo))
        if not todo:
            break
    for r in range(rounds):
        br = brackets()
        mids = sorted({round(0.5 * (lo + hi), 12) for lo, hi in br.values()
                       if lo is not None and hi is not None and hi - lo > 1e-6 * lsb})
        if not mids:
            break
        codes = eng.convert(mids, f"{label}_r{r}", rd)
        pts.extend(zip(mids, codes.tolist()))
    br = brackets()
    T = {k: (0.5 * (lo + hi) if lo is not None and hi is not None else np.nan) for k, (lo, hi) in br.items()}
    width = {k: (hi - lo if lo is not None and hi is not None else np.nan) for k, (lo, hi) in br.items()}
    return T, width, pts


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    rd = run_dir(ctx)
    tim = ensure_timing(ctx)
    t_conv = tim["t_conv_period"]
    eng = AdcEngine(ctx, a.variant, t_conv=t_conv, t_sf_rel=tim.get("t_sf_rel"), label="static",
                    fsm_model=a.fsm_model or c.FSM_MODEL, ls_model=a.ls_model or c.LS_MODEL)
    if a.cap_mismatch > 0:
        txt, vals = cdac_mismatch_text(ctx.lib, c, a.cap_mismatch, a.seed)
        eng.overrides["cdac_caps_10b_diff"] = txt
        rep.data["cap_values_units"] = vals
        rep.note(f"CDAC mismatch: sigma(Cu)={a.cap_mismatch*100:.3g}% seed={a.seed}")
    lsb, n = c.LSB, c.NBITS
    rep.note("voltage domains: " + eng.dom.describe())
    for nt in eng.dom.notes:
        rep.note(nt)
    rep.note(f"method={a.method}, variant={a.variant}, FSM model={eng.fsm_model}, "
             f"conversion period {t_conv*1e9:.4g} ns (from adc_timing)")

    if a.method == "hist":
        hits = 2 if a.quick else a.hits
        step = lsb / hits
        v = np.arange(-c.VFS / 2 - 2 * lsb, c.VFS / 2 + 2 * lsb, step)
        rep.note(f"histogram: {len(v)} conversions ({hits}/code) -> DNL resolution {1/hits:.3g} LSB")
        codes = eng.convert(v, "hist", rd)
        good = codes >= 0
        T = metrics.transitions_from_staircase(v[good], codes[good], c.NCODES)
        rep.add("conversions without valid", int(np.sum(~good)), "", 0, "<=")
        st = metrics.static_from_transitions(T, lsb, c.VFS)
        model = None
    else:
        if a.method == "bitweights":
            ks = metrics.major_carry_codes(n)
            if a.quick:
                ks = [k for k in ks if k in (1, 2, 3, 255, 256, 511, 512, 513, 767, 768, 1022, 1023)
                      or k in (2 ** i for i in range(n))]
        else:
            ks = list(range(1, c.NCODES)) if a.codes == "all" else [int(x) for x in a.codes.split(",")]
        rounds = 4 if a.quick else a.rounds
        Tm, width, pts = search_transitions(eng, ks, rounds, rd, c, a.method)
        res = np.nanmax(list(width.values())) / lsb
        rep.add("transition resolution (worst bracket)", res, "LSB", 0.1, "<=")
        rep.add("conversions used", len(pts))
        unresolved = [k for k, x in Tm.items() if np.isnan(x)]
        if unresolved:
            rep.note(f"could not bracket transitions {unresolved[:10]}...")
        kk = np.array([k for k in ks if not np.isnan(Tm[k])])
        TT = np.array([Tm[k] for k in kk])
        rep.data["measured_transitions"] = {int(k): float(Tm[k]) for k in kk}
        # model-free DNL where both edges of a code were measured
        direct = [(k, (Tm[k + 1] - Tm[k]) / lsb - 1) for k in kk if (k + 1) in Tm and not np.isnan(Tm[k + 1])]
        if direct:
            kd, dd = max(direct, key=lambda x: abs(x[1]))
            rep.add("measured DNL, worst major carry", dd, "LSB", c.SPEC["dnl_lsb"], "abs<=",
                    f"code {kd} (model-free: both edges simulated)")
        if a.method == "bitweights":
            W, off, resid = metrics.fit_bit_weights(kk, TT, n)
            rep.add("bit-weight model fit residual (max)", float(np.max(np.abs(resid)) / lsb), "LSB", 0.1, "<=",
                    "large -> the SAR/superposition model does not describe this ADC; use --method hist")
            T = metrics.sar_transitions(W, off)
            model = {"weights_lsb": (W / lsb).tolist(), "offset": off, "resid_lsb": (resid / lsb).tolist()}
            rep.data["bit_weights_lsb"] = model["weights_lsb"]
            for i in range(n - 1, n - 4, -1):
                rep.add(f"bit {i} weight", W[i] / lsb, "LSB", desc=f"ideal {2 ** i}")
        else:
            T = np.full(c.NCODES, np.nan)
            for k in kk:
                T[k] = Tm[k]
            model = None
        st = metrics.static_from_transitions(T, lsb, c.VFS)

    rep.add("DNL max", st["dnl_max"], "LSB", c.SPEC["dnl_lsb"], "abs<=")
    rep.add("DNL min", st["dnl_min"], "LSB", c.SPEC["dnl_lsb"], "abs<=")
    rep.add("INL max (endpoint)", st["inl_max"], "LSB", c.SPEC["inl_lsb"], "abs<=")
    rep.add("INL min (endpoint)", st["inl_min"], "LSB", c.SPEC["inl_lsb"], "abs<=")
    rep.add("INL max (best fit)", st["inl_bf_max"], "LSB")
    rep.add("INL min (best fit)", st["inl_bf_min"], "LSB")
    rep.add("missing codes", len(st["missing_codes"]), "", 0, "<=")
    rep.add("monotonic", int(st["monotonic"]), "", 1, "==")
    rep.add("offset error", st["offset_lsb"], "LSB", desc="vs ideal T(k) = -VFS/2 + k*LSB")
    rep.add("gain error", st["gain_error"] * 100, "%")
    if st["missing_codes"]:
        rep.note(f"missing codes: {st['missing_codes'][:20]}")
    rep.data.update({"dnl": st["dnl"].tolist(), "dnl_codes": st["dnl_codes"].tolist(),
                     "inl": st["inl_ep"].tolist(), "inl_codes": st["inl_codes"].tolist()})

    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    ax[0].plot(st["dnl_codes"], st["dnl"], lw=0.7)
    ax[0].set(ylabel="DNL [LSB]", title=f"static linearity ({a.method}, {a.variant})")
    ax[1].plot(st["inl_codes"], st["inl_ep"], lw=0.7, label="endpoint")
    ax[1].plot(st["inl_codes"], st["inl_bf"], lw=0.7, label="best fit")
    if a.method != "hist":
        ax[1].plot(list(rep.data["measured_transitions"].keys()),
                   [(Tv - (st["T"][0] + (k - st["codes_T"][0]) * st["lsb_measured"])) / st["lsb_measured"]
                    for k, Tv in rep.data["measured_transitions"].items()], "o", ms=3, label="simulated points")
    ax[1].set(xlabel="code", ylabel="INL [LSB]")
    ax[1].legend()
    fig.tight_layout()
    rep.plot(fig, "static.png")
