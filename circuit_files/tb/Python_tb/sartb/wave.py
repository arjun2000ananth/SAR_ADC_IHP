"""Waveform post-processing helpers (numpy only)."""
from __future__ import annotations

import numpy as np


def crossings(t, y, level, direction: str = "both", t_min: float = -np.inf, t_max: float = np.inf):
    """Linear-interpolated times where y crosses `level`."""
    t = np.asarray(t)
    y = np.asarray(y) - level
    s = np.sign(y)
    s[s == 0] = 1
    idx = np.nonzero(s[:-1] != s[1:])[0]
    out = []
    for i in idx:
        rising = y[i + 1] > y[i]
        if direction == "rise" and not rising:
            continue
        if direction == "fall" and rising:
            continue
        dy = y[i + 1] - y[i]
        tc = t[i] if dy == 0 else t[i] - y[i] * (t[i + 1] - t[i]) / dy
        if t_min <= tc <= t_max:
            out.append(tc)
    return np.array(out)


def first_crossing(t, y, level, direction="both", t_min=-np.inf, t_max=np.inf):
    c = crossings(t, y, level, direction, t_min, t_max)
    return float(c[0]) if len(c) else float("nan")


def value_at(t, y, tq):
    return np.interp(tq, t, y)


def sample_after(t, y, tq):
    """First stored sample at or after tq (no interpolation -> safe for digital codes)."""
    i = np.searchsorted(t, tq)
    i = np.clip(i, 0, len(t) - 1)
    return np.asarray(y)[i]


def window(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return t[m], np.asarray(y)[m]


def average(t, y, t0, t1):
    tw, yw = window(t, y, t0, t1)
    if len(tw) < 2:
        return float(value_at(t, y, 0.5 * (t0 + t1)))
    return float(np.trapezoid(yw, tw) / (tw[-1] - tw[0])) if hasattr(np, "trapezoid") \
        else float(np.trapz(yw, tw) / (tw[-1] - tw[0]))


def integral(t, y, t0, t1):
    tw, yw = window(t, y, t0, t1)
    if len(tw) < 2:
        return 0.0
    f = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    return float(f(yw, tw))


def settling_time(t, y, t0, final, tol, t_end=None):
    """Time after t0 at which |y-final| enters and stays within tol (nan if never)."""
    t_end = t[-1] if t_end is None else t_end
    tw, yw = window(t, y, t0, t_end)
    if len(tw) == 0:
        return float("nan")
    bad = np.nonzero(np.abs(yw - final) > tol)[0]
    if len(bad) == 0:
        return 0.0
    i = bad[-1]
    if i >= len(tw) - 1:
        return float("nan")
    return float(tw[i + 1] - t0)


def digital(y, vdd):
    return (np.asarray(y) > 0.5 * vdd).astype(int)


def pulses(t, y, thr):
    """List of (t_rise, t_fall) for high pulses."""
    r = crossings(t, y, thr, "rise")
    f = crossings(t, y, thr, "fall")
    out = []
    for tr in r:
        nf = f[f > tr]
        out.append((tr, float(nf[0]) if len(nf) else float("nan")))
    return out
