"""ADC figures of merit: FFT metrics, INL/DNL, SAR bit-weight model."""
from __future__ import annotations

import math

import numpy as np
# Coherent sampling

def coherent_bin(n: int, fs: float, f_target: float) -> int:
    """Odd bin M, coprime with N, closest to f_target (M < N/2)."""
    m = max(1, int(round(f_target / fs * n)))
    m = min(m, n // 2 - 1)
    cands = sorted(range(1, n // 2), key=lambda k: (abs(k - m), -k))
    for k in cands:
        if math.gcd(k, n) == 1:
            return k
    return 1
# Spectrum metrics
def _fold(b: int, n: int) -> int:
    b %= n
    return n - b if b > n // 2 else b


def fft_metrics(codes, nbits: int, fs: float, sig_bin: int | None = None, n_harm: int = 9,
                window: str = "rect", span: int | None = None) -> dict:
    """SNR/SINAD/SFDR/THD/ENOB from ADC output codes.

    window='rect' requires coherent sampling (sig_bin = cycles in record).
    window='bh4' (Blackman-Harris 4-term) for non-coherent data; span = bins per tone side.
    """
    x = np.asarray(codes, dtype=float)
    n = len(x)
    x = x - x.mean()
    if window == "rect":
        w = np.ones(n)
        span = 0 if span is None else span
    elif window == "bh4":
        k = np.arange(n)
        a = (0.35875, 0.48829, 0.14128, 0.01168)
        w = (a[0] - a[1] * np.cos(2 * np.pi * k / n) + a[2] * np.cos(4 * np.pi * k / n)
             - a[3] * np.cos(6 * np.pi * k / n))
        span = 4 if span is None else span
    else:
        raise ValueError(window)
    X = np.fft.rfft(x * w)
    cg = w.sum()                                     # coherent gain
    enbw = n * np.sum(w ** 2) / cg ** 2              # noise bandwidth in bins
    p = (np.abs(X) / cg) ** 2
    p[1:] *= 2.0
    if n % 2 == 0:
        p[-1] /= 2.0
    nb = len(p)
    if sig_bin is None:
        sig_bin = int(np.argmax(p[1 + span:])) + 1 + span

    def band(b):
        return np.arange(max(0, b - span), min(nb, b + span + 1))

    used = np.zeros(nb, bool)
    dc = band(0)
    used[dc] = True
    sig = band(sig_bin)
    ps = p[sig].sum()
    used[sig] = True
    harm_bins, ph_each = [], []
    for h in range(2, n_harm + 1):
        hb = _fold(h * sig_bin, n)
        idx = band(hb)
        idx = idx[~used[idx]]
        if len(idx) == 0:
            continue
        harm_bins.append(hb)
        ph_each.append(p[idx].sum())
        used[idx] = True
    ph = float(np.sum(ph_each))
    pn = p[~used].sum()
    if window != "rect":
        ps /= enbw
        ph /= enbw
        pn /= enbw
    # spur search excludes DC and signal only
    spur = p.copy()
    spur[dc] = 0
    spur[sig] = 0
    if span:
        # integrate each candidate spur over its band
        spur_pw = np.convolve(spur, np.ones(2 * span + 1), mode="same") / enbw
    else:
        spur_pw = spur
    i_spur = int(np.argmax(spur_pw))
    p_spur = spur_pw[i_spur]
    fs_amp = 2 ** nbits / 2
    p_fs = fs_amp ** 2 / 2
    amp = math.sqrt(2 * ps)
    sinad = 10 * math.log10(ps / (pn + ph))
    snr = 10 * math.log10(ps / pn)
    thd = 10 * math.log10(ph / ps) if ph > 0 else -300.0
    sfdr = 10 * math.log10(ps / p_spur) if p_spur > 0 else 300.0
    dbfs = 20 * math.log10(amp / fs_amp)
    spectrum_dbfs = 10 * np.log10(np.maximum(p, 1e-30) / p_fs)
    return {
        "N": n, "fs": fs, "sig_bin": int(sig_bin), "fin": sig_bin * fs / n,
        "amp_codes": amp, "amp_dbfs": dbfs,
        "snr_db": snr, "sinad_db": sinad, "thd_db": thd, "sfdr_dbc": sfdr,
        "sfdr_dbfs": sfdr - dbfs, "enob": (sinad - 1.76) / 6.02,
        "enob_fs": (sinad - dbfs - 1.76) / 6.02,
        "harmonics_dbc": {f"H{h}": 10 * math.log10(v / ps) if v > 0 else -300.0
                          for h, v in zip(range(2, 2 + len(ph_each)), ph_each)},
        "spur_bin": i_spur, "noise_floor_dbfs_per_bin": 10 * math.log10(max(pn, 1e-30) / (nb - used.sum()) / p_fs),
        "freq": np.arange(nb) * fs / n, "spectrum_dbfs": spectrum_dbfs, "harm_bins": harm_bins,
    }


def ideal_sndr(nbits: int) -> float:
    return 6.02 * nbits + 1.76


def add_noise_to_snr(snr_db: float, sig_power: float, noise_power: float) -> float:
    """Combine a simulated SNR with extra (e.g. thermal) noise power (same units as sig_power)."""
    pn_sim = sig_power / 10 ** (snr_db / 10)
    return 10 * math.log10(sig_power / (pn_sim + noise_power))

# Static linearity
def transitions_from_staircase(vin, codes, ncodes: int) -> np.ndarray:
    """Histogram-style transition estimate for a uniform, increasing input staircase.

    T[k] (k=1..ncodes-1) = v0 + step*count(code<k), v0 = first input - step/2.
    Robust to non-monotonic/noisy data (this is the standard ramp-histogram method).
    """
    vin = np.asarray(vin, float)
    codes = np.asarray(codes, int)
    step = np.median(np.diff(vin))
    v0 = vin[0] - step / 2
    hist = np.bincount(np.clip(codes, 0, ncodes - 1), minlength=ncodes)
    cum = np.cumsum(hist)
    T = np.full(ncodes, np.nan)
    T[1:] = v0 + step * cum[:-1]
    return T


def static_from_transitions(T, lsb_ideal: float, vfs: float, ideal_first: float | None = None) -> dict:
    """INL/DNL from transition voltages T[k] (k=1..ncodes-1; T[0] ignored).

    DNL uses the endpoint-fit LSB (T[last]-T[1])/(ncodes-2); INL is reported both
    endpoint-fit and best-fit (least squares line through T).
    """
    T = np.asarray(T, float)
    ncodes = len(T)
    k = np.arange(ncodes)
    valid = ~np.isnan(T)
    valid[0] = False
    kk = k[valid]
    TT = T[valid]
    if len(kk) < 3:
        raise ValueError("not enough transitions")
    lsb_ep = (TT[-1] - TT[0]) / (kk[-1] - kk[0])
    inl_ep = (TT - (TT[0] + (kk - kk[0]) * lsb_ep)) / lsb_ep
    a, b = np.polyfit(kk, TT, 1)
    inl_bf = (TT - (a * kk + b)) / a
    # DNL only between consecutive measured transitions
    cons = np.diff(kk) == 1
    widths = np.diff(TT)[cons]
    dnl_codes = kk[:-1][cons]
    dnl = widths / lsb_ep - 1.0
    missing = dnl_codes[widths <= 0.0].tolist()
    if ideal_first is None:
        ideal_first = -vfs / 2 + lsb_ideal          # T[1] of an ideal converter
    ideal_T = ideal_first + (kk - 1) * lsb_ideal
    offset_lsb = float(np.mean(TT - ideal_T) / lsb_ideal) if len(kk) else float("nan")
    gain_err = float(lsb_ep / lsb_ideal - 1.0)
    return {
        "codes_T": kk, "T": TT, "dnl_codes": dnl_codes, "dnl": dnl, "inl_codes": kk,
        "inl_ep": inl_ep, "inl_bf": inl_bf,
        "dnl_max": float(np.max(dnl)) if len(dnl) else float("nan"),
        "dnl_min": float(np.min(dnl)) if len(dnl) else float("nan"),
        "inl_max": float(np.max(inl_ep)), "inl_min": float(np.min(inl_ep)),
        "inl_bf_max": float(np.max(inl_bf)), "inl_bf_min": float(np.min(inl_bf)),
        "lsb_measured": float(lsb_ep), "gain_error": gain_err, "offset_lsb": offset_lsb,
        "missing_codes": missing, "monotonic": bool(np.all(np.diff(TT) >= 0)),
    }



# Binary-search (SAR) model from bit weights

def _bits(nbits):
    k = np.arange(2 ** nbits)
    return ((k[:, None] >> np.arange(nbits)[None, :]) & 1).astype(float)  # [code, bit] LSB first


def sar_transitions(weights, offset: float) -> np.ndarray:
    """Transition voltages T[k] (k>=1) of a binary-search ADC with DAC weights (LSB first).

    decision for bit i: v > offset + sum_{j>i} b_j W_j + W_i
    Handles non-binary weights (missing codes -> zero width).
    """
    W = np.asarray(weights, float)
    nb = len(W)
    B = _bits(nb)
    n = 2 ** nb
    L = offset + B @ W
    U = np.full(n, np.inf)
    for c in range(n):
        best = np.inf
        for i in range(nb):
            if B[c, i] == 0:
                thr = offset + np.dot(B[c, i + 1:], W[i + 1:]) + W[i]
                best = min(best, thr)
        U[c] = best
    exists = U > L
    T = np.full(n, np.nan)
    nxt = None
    for c in range(n - 1, 0, -1):
        if exists[c]:
            nxt = L[c]
        T[c] = nxt if nxt is not None else np.inf
    return T


def fit_bit_weights(codes_k, T_k, nbits: int) -> tuple[np.ndarray, float, np.ndarray]:
    """Least-squares fit of T_k = off + sum b_i(k) W_i. Returns (W, off, residuals)."""
    codes_k = np.asarray(codes_k, int)
    B = _bits(nbits)[codes_k]
    A = np.hstack([np.ones((len(codes_k), 1)), B])
    sol, *_ = np.linalg.lstsq(A, np.asarray(T_k, float), rcond=None)
    resid = np.asarray(T_k) - A @ sol
    return sol[1:], float(sol[0]), resid


def major_carry_codes(nbits: int) -> list[int]:
    n = 2 ** nbits
    ks = {1, 2, 3, n - 1, n - 2}
    for i in range(1, nbits):
        for base in (0, n // 2):
            for c in (base + 2 ** i - 1, base + 2 ** i):
                if 1 <= c <= n - 1:
                    ks.add(c)
    return sorted(ks)

# Comparator helpers


def kT_over_C(c: float, temp_c: float = 27.0) -> float:
    return 1.380649e-23 * (temp_c + 273.15) / c
