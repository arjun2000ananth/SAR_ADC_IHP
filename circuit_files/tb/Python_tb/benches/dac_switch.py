"""DAC bottom-plate switch (dac_sw_2to1_tg): Ron of vref/vcm paths, per-bit settling, break-before-make (crowbar)."""
from __future__ import annotations

import math

import numpy as np

from sartb import wave
from sartb.spice import fmt, run_many

from .common import dac_window, deck, instance_line, plt, run_dir

SW = "dac_sw_2to1_tg"


def add_args(p):
    p.add_argument("--rref", type=float, default=0.0, help="series resistance of the vrefp/vcm sources [Ohm]")
    p.add_argument("--tbit", type=float, default=None, help="time available to settle (default 1 CLK period)")


def _sw(sc, inst, sel, out, vref="vrefp", vcm="vcm"):
    return instance_line(inst, sc, {"sel": sel, "out": out, "vss": "vss", "vdd": "vdd", "vref": vref, "vcm": vcm})


def run(ctx, a):
    c, rep = ctx.cfg, ctx.rep
    sc = ctx.lib.get(SW)
    rd = run_dir(ctx)
    n = c.NBITS
    ctot = c.CU * 2 ** n
    tbit, tbit_src = (a.tbit, "--tbit") if a.tbit else dac_window(c)
    rep.note(f"settling budget {tbit*1e9:.3g} ns ({tbit_src})")

    # Ron of both paths (DC, 1 uA test current)
    decks = []
    for sel, name in ((c.VDD, "vref path"), (0.0, "vcm path")):
        d = deck(ctx, f"Ron {name}")
        d.use(SW)
        d.add(f"Vvdd vdd 0 {c.VDD}", "Vvss vss 0 0", f"Vsel sel 0 {sel}",
              f"Vvref vrefp 0 {c.VREFP}", f"Vvcm vcm 0 {c.VCM}", "Itest out 0 1u")
        d.add(_sw(sc, "xdut", "sel", "out"))
        d.control("op")
        d.control("print v(out)")
        d.wrdata("op.txt", ["v(out)"])
        decks.append((d, "ron_ref" if sel else "ron_cm"))

    # per-bit settling: each switch drives C_i in series with (Ctot - C_i0
    T = 4 * tbit
    d = deck(ctx, "per-bit settling")
    d.use(SW)
    d.add(f"Vvdd vdd 0 {c.VDD}", "Vvss vss 0 0")
    if a.rref > 0:
        d.add(f"Vvref0 vref0 0 {c.VREFP}", f"Rref vref0 vrefp {a.rref}",
              f"Vvcm0 vcm0 0 {c.VCM}", f"Rcm vcm0 vcm {a.rref}")
    else:
        d.add(f"Vvref vrefp 0 {c.VREFP}", f"Vvcm vcm 0 {c.VCM}")
    d.add(f"Vsel sel 0 PULSE(0 {c.VDD} {fmt(T / 4)} {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} {fmt(T / 2)} {fmt(T)})")
    for i in range(n):
        ci = c.CU * 2 ** i
        d.add(_sw(sc, f"xsw{i}", "sel", f"b{i}"),
              f"Cb{i} b{i} top{i} {ci}", f"Ct{i} top{i} 0 {ctot - ci}",
              f"Rt{i} top{i} 0 1e12")
    d.control(f"tran {fmt(T / 4000)} {fmt(1.5 * T)}")
    vecs = [f"v(b{i})" for i in range(n)] + [f"v(top{i})" for i in range(n)] + ["v(sel)"]
    if a.rref > 0:
        vecs += ["v(vrefp)", "v(vcm)"]
    vecs += ["i(vvref)" if a.rref == 0 else "i(vvref0)"]
    d.wrdata("settle.txt", vecs)
    decks.append((d, "settle"))
    res = run_many(c, decks, rd, "dac switch")

    ron = {}
    for r, key, vsrc in ((res[0], "vref", c.VREFP), (res[1], "vcm", c.VCM)):
        vout = r.data()["v(out)"][0]
        ron[key] = abs(vout - vsrc) / 1e-6
    rep.add("Ron vref path (sel=1)", ron["vref"], "Ohm", desc=f"passing {c.VREFP} V")
    rep.add("Ron vcm path (sel=0)", ron["vcm"], "Ohm", desc=f"passing {c.VCM} V")
    if c.VREFP >= c.VDD - 0.3:
        rep.note("vrefp is at/near VDD: only the PMOS of the vref tg conducts (NMOS has ~0 Vgs)")

    s = res[2].data()
    t = s["t"]
    t_up, t_dn = T / 4, 3 * T / 4
    lsb_top = c.LSB              # an error on one top plate is a differential error at the comparator
    worst = {"up": 0.0, "dn": 0.0}
    rows = []
    for i in range(n):
        top = s[f"v(top{i})"]
        f_up = wave.value_at(t, top, t_dn - 1e-12)
        f_dn = wave.value_at(t, top, 1.25 * T - 1e-12)      # before sel rises again at T + T/4
        su = wave.settling_time(t, top, t_up, f_up, 0.5 * lsb_top, t_dn)
        sd = wave.settling_time(t, top, t_dn, f_dn, 0.5 * lsb_top, 1.25 * T - 1e-12)
        ci = c.CU * 2 ** i
        ceff = ci * (ctot - ci) / ctot
        rows.append((i, su, sd, ceff))
        worst["up"] = max(worst["up"], su if not math.isnan(su) else np.inf)
        worst["dn"] = max(worst["dn"], sd if not math.isnan(sd) else np.inf)
    for i, su, sd, ceff in rows[::-1][:3]:
        rep.add(f"bit {i} settle to 0.5LSB (vcm->vref)", su, "s", desc=f"Ceff={ceff*1e12:.3g} pF")
        rep.add(f"bit {i} settle to 0.5LSB (vref->vcm)", sd, "s")
    rep.add("worst settling, all bits", max(worst.values()), "s", tbit, "<=",
            f"top-plate within 0.5 LSB; available {tbit*1e9:.3g} ns")
    # crowbar: vref source current spike when sel toggles
    iref = s[vecs[-1]]
    m = (t > t_up - 1e-9) & (t < t_up + 2e-9)
    q_step = float(-wave.integral(t, iref, t_up - 1e-9, t_up + tbit))
    rep.add("charge from vref, one full-set step", q_step, "C", desc="all 10 switches toggling together")
    rep.add("peak vref current at switching", float(np.max(np.abs(iref[m]))), "A")
    if a.rref > 0:
        rep.add("vrefp droop (with rref)", float(c.VREFP - s["v(vrefp)"].min()), "V")
    rep.data["settle"] = [{"bit": i, "up": su, "dn": sd, "ceff": ce} for i, su, sd, ce in rows]

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].semilogy([r[0] for r in rows], [r[1] * 1e9 for r in rows], "o-", label="vcm->vref")
    ax[0].semilogy([r[0] for r in rows], [r[2] * 1e9 for r in rows], "s--", label="vref->vcm")
    ax[0].axhline(tbit * 1e9, ls=":", c="r", label="available")
    ax[0].set(xlabel="bit", ylabel="settling to 0.5 LSB [ns]", title="per-bit top-plate settling")
    ax[0].legend()
    mm = (t > t_up - 1e-9) & (t < t_up + tbit)
    i = n - 1
    ax[1].plot((t[mm] - t_up) * 1e9, s[f"v(b{i})"][mm], label=f"bottom b{i}")
    ax[1].plot((t[mm] - t_up) * 1e9, s[f"v(top{i})"][mm], label="top (series cap)")
    ax[1].set(xlabel="t [ns]", ylabel="V", title="MSB switch step")
    ax[1].legend()
    fig.tight_layout()
    rep.plot(fig, "dac_switch.png")
