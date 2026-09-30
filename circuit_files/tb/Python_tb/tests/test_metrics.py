"""Self-checks for the metric code (no ngspice needed):  python tests/test_metrics.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sartb import metrics as M  # noqa: E402

NB = 10
FS = 3.3
LSB = FS / 2 ** NB


def quantize(v):
    return np.clip(np.floor((v + FS / 2) / LSB), 0, 2 ** NB - 1).astype(int)


def test_ideal_sndr():
    n, fs = 4096, 1e6
    m = M.coherent_bin(n, fs, 0.1e6)
    t = np.arange(n) / fs
    v = (FS / 2) * 0.999 * np.sin(2 * np.pi * m * fs / n * t + 0.3)
    r = M.fft_metrics(quantize(v), NB, fs, m)
    assert abs(r["sinad_db"] - M.ideal_sndr(NB)) < 0.5, r["sinad_db"]
    assert abs(r["enob"] - NB) < 0.1, r["enob"]


def test_distortion():
    n, fs = 2048, 1e6
    m = M.coherent_bin(n, fs, 0.2e6)
    t = np.arange(n) / fs
    x = np.sin(2 * np.pi * m * fs / n * t)
    v = (FS / 2) * 0.9 * (x + 1e-3 * x ** 3)  # HD3 of ~ 1e-3*0.25 -> -72 dBc
    r = M.fft_metrics(quantize(v), NB, fs, m)
    assert -76 < r["harmonics_dbc"]["H3"] < -68, r["harmonics_dbc"]
    assert r["sfdr_dbc"] < 76


def test_noncoherent_window():
    n, fs = 4096, 1e6
    t = np.arange(n) / fs
    v = (FS / 2) * 0.9 * np.sin(2 * np.pi * 123.4e3 * t)
    r = M.fft_metrics(quantize(v), NB, fs, None, window="bh4")
    assert abs(r["sinad_db"] - (M.ideal_sndr(NB) + 20 * np.log10(0.9))) < 1.5, r["sinad_db"]


def test_static_ideal_and_weights():
    W = 2.0 ** np.arange(NB) * LSB
    T = M.sar_transitions(W, -FS / 2)
    s = M.static_from_transitions(T, LSB, FS)
    assert max(abs(s["dnl_max"]), abs(s["dnl_min"])) < 1e-9
    assert max(abs(s["inl_max"]), abs(s["inl_min"])) < 1e-9
    assert abs(s["offset_lsb"]) < 1e-9
    # MSB 1 LSB too big -> DNL(+1) at 511, INL step
    W2 = W.copy()
    W2[9] += LSB
    s2 = M.static_from_transitions(M.sar_transitions(W2, -FS / 2), LSB, FS)
    i = list(s2["dnl_codes"]).index(511)
    assert abs(s2["dnl"][i] - 1.0) < 0.01, s2["dnl"][i]
    # MSB 1 LSB too small -> missing code 511
    W3 = W.copy()
    W3[9] -= LSB
    s3 = M.static_from_transitions(M.sar_transitions(W3, -FS / 2), LSB, FS)
    assert 511 in s3["missing_codes"], s3["missing_codes"]
    # fit recovers weights from major-carry transitions
    ks = M.major_carry_codes(NB)
    Wf, off, res = M.fit_bit_weights(ks, M.sar_transitions(W2, -FS / 2)[ks], NB)
    assert np.allclose(Wf, W2, atol=1e-9) and abs(off + FS / 2) < 1e-9


def test_staircase_hist():
    step = LSB / 8
    v = np.arange(-FS / 2 - 4 * LSB, FS / 2 + 4 * LSB, step)
    T = M.transitions_from_staircase(v, quantize(v), 2 ** NB)
    s = M.static_from_transitions(T, LSB, FS)
    assert max(abs(s["dnl_max"]), abs(s["dnl_min"])) <= 0.126
    assert abs(s["offset_lsb"]) < 0.2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
