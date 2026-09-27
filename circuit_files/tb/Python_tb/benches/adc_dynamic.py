"""Full ADC dynamic performance: coherent sine FFT  SNR, SINAD, ENOB, SFDR, THD (+ kT/C estimate, FoM)."""
from __future__ import annotations

import math

import numpy as np

from sartb import metrics
from sartb.adc import AdcEngine, cdac_mismatch_text

from .common import ensure_timing, plt, run_dir


def add_args(p):
    p.add_argument("--n", type=int, default=256, help="FFT length (conversions per test)")
    p.add_argument("--fin", default="low,nyq", help="comma list: low (~fs/10), nyq (~fs/2) or a frequency in Hz")
    p.add_argument("--amp-dbfs", type=float, default=-1.0)
    p.add_argument("--variant", choices=["real", "ideal"], default="real")
    p.add_argument("--fsm-model", choices=["xspice", "spice"], default=None)
    p.add_argument("--ls-model", choices=["xspice", "spice"], default=None,
                   help="level shifters: in the XSPICE bridges (fast) or transistor level")
    p.add_argument("--cap-mismatch", type=float, default=0.0, help="relative sigma of one unit cap")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--comp-noise", type=float, default=0.0,
                   help="comparator input-referred rms noise [V] for the noise estiimate")


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    rd = run_dir(ctx)
    tim = ensure_timing(ctx)
    t_conv = tim["t_conv_period"]
    fs = 1 / t_conv
    eng = AdcEngine(ctx, a.variant, t_conv=t_conv, t_sf_rel=tim.get("t_sf_rel"), label="dyn",
                    fsm_model=a.fsm_model or c.FSM_MODEL, ls_model=a.ls_model or c.LS_MODEL)
    if a.cap_mismatch > 0:
        txt, _ = cdac_mismatch_text(ctx.lib, c, a.cap_mismatch, a.seed)
        eng.overrides["cdac_caps_10b_diff"] = txt
        rep.note(f"CDAC mismatch: sigma(Cu)={a.cap_mismatch*100:.3g}% seed={a.seed}")
    n = 64 if a.quick else a.n
    amp = 10 ** (a.amp_dbfs / 20) * c.VFS / 2          # differential peak
    t_sf = tim.get("t_sf_rel") or 0.0
    rep.note("voltage domains: " + eng.dom.describe())
    for nt in eng.dom.notes:
        rep.note(nt)
    rep.note(f"fs={fs/1e6:.4g} MS/s (period from adc_timing), N={n}, {a.amp_dbfs} dBFS, variant={a.variant}, "
             f"FSM model={eng.fsm_model}")
    ctot = c.CU * 2 ** c.NBITS
    p_sig = amp ** 2 / 2
    p_ktc = 2 * metrics.kT_over_C(ctot, c.TEMP)
    p_comp = a.comp_noise ** 2
    fom_e = tim.get("energy_per_conv")

    results = {}
    for spec in a.fin.split(","):
        spec = spec.strip()
        f_t = 0.1 * fs if spec == "low" else (0.49 * fs if spec == "nyq" else float(spec))
        m = metrics.coherent_bin(n, fs, f_t)
        fin = m * fs / n
        codes = eng.convert_sine(n, amp, fin, f"sine_{spec}", rd)
        miss = int(np.sum(codes < 0))
        tag = f"[{spec} {fin/1e3:.4g} kHz]"
        rep.add(f"{tag} conversions without valid", miss, "", 0, "<=")
        if miss:
            codes = np.where(codes < 0, int(np.median(codes[codes >= 0])), codes)
        fm = metrics.fft_metrics(codes, c.NBITS, fs, m)
        results[spec] = (fm, codes, fin)
        rep.add(f"{tag} SNDR", fm["sinad_db"], "dB", c.SPEC["sndr_db"], ">=")
        rep.add(f"{tag} SNR", fm["snr_db"], "dB")
        rep.add(f"{tag} THD", fm["thd_db"], "dB")
        rep.add(f"{tag} SFDR", fm["sfdr_dbc"], "dBc", c.SPEC["sfdr_db"], ">=")
        rep.add(f"{tag} ENOB", fm["enob"], "bits", c.SPEC["enob"], ">=")
        rep.add(f"{tag} ENOB (FS-referred)", fm["enob_fs"], "bits")
        rep.add(f"{tag} signal amplitude", fm["amp_dbfs"], "dBFS")
        # sine fit at the known frequency: amplitude/offset/effective sampling instant
        g = np.arange(n)
        tk = g * t_conv + t_sf
        A = np.column_stack([np.sin(2 * math.pi * fin * tk), np.cos(2 * math.pi * fin * tk), np.ones(n)])
        coef, *_ = np.linalg.lstsq(A, codes.astype(float), rcond=None)
        amp_fit = math.hypot(coef[0], coef[1]) * c.LSB           # differential volts
        ph = math.atan2(coef[1], coef[0])                        # fit = amp*sin(w t + ph)
        delay = -ph / (2 * math.pi * fin)
        resid = codes - A @ coef
        rep.add(f"{tag} gain (fitted amp / applied)", amp_fit / amp, "x")
        rep.add(f"{tag} effective sampling delay", delay, "s",
                desc="fitted phase vs `sample` falling edge; ~ RC tracking lag of the TG")
        rep.add(f"{tag} rms residual after sine fit", float(np.sqrt(np.mean(resid ** 2))), "LSB",
                desc="ideal quantiser: 0.289 LSB")
        # noise-inclusive estimate (transient sim has no device noise)
        sndr_est = metrics.add_noise_to_snr(fm["sinad_db"], p_sig, p_ktc + p_comp)
        rep.add(f"{tag} SNDR incl. kT/C{' + comp noise' if p_comp else ''} (estimate)", sndr_est, "dB")
        if fom_e:
            enob = fm["enob"]
            rep.add(f"{tag} Walden FoM", fom_e / 2 ** enob, "J/step",
                    desc="energy/conversion from adc_timing / 2^ENOB")
        rep.data[f"fft_{spec}"] = {k: v for k, v in fm.items() if not isinstance(v, np.ndarray)}
        rep.data[f"codes_{spec}"] = codes.tolist()

    rep.add("kT/C noise (diff rms)", math.sqrt(p_ktc) / c.LSB, "LSB", desc=f"Ctot/side={ctot*1e12:.3g} pF")

    k = len(results)
    fig, ax = plt.subplots(k, 2, figsize=(12, 4 * k), squeeze=False)
    for row, (spec, (fm, codes, fin)) in enumerate(results.items()):
        ax[row, 0].plot(fm["freq"] / 1e3, fm["spectrum_dbfs"], lw=0.8)
        for hb in fm["harm_bins"][:5]:
            ax[row, 0].plot(fm["freq"][hb] / 1e3, fm["spectrum_dbfs"][hb], "rv", ms=4)
        ax[row, 0].set(xlabel="f [kHz]", ylabel="dBFS", ylim=(-130, 5),
                       title=f"fin={fin/1e3:.4g} kHz  SNDR={fm['sinad_db']:.2f} dB  ENOB={fm['enob']:.2f}  "
                             f"SFDR={fm['sfdr_dbc']:.1f} dBc")
        ax[row, 1].plot(codes, ".", ms=3)
        ax[row, 1].set(xlabel="sample", ylabel="code", title="output codes")
    fig.tight_layout()
    rep.plot(fig, "dynamic.png")
