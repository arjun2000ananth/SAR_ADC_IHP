"""
Full-ADC conversion engine: builds chunked ngspice decks around the sar_10_bit subckt,
runs them in parallel and returns one output code per conversion.

variant='real'  : the netlist exactly as designed (sar_10_bit)
variant='ideal' : same FSM + comparator + CDAC caps, but ideal sampling switches and
                  ideal DAC switches  (used to verify the FSM / algorithm in isolation)
"""
from __future__ import annotations

import math
import os

import numpy as np

from . import wave
from .spice import Deck, fmt, pwl, run_many

IDEALIZED = {"tg", "inverter", "dac_sw_2to1_tg"}


class AdcEngine:
    def __init__(self, ctx, variant: str = "real", t_conv: float | None = None,
                 t_sf_rel: float | None = None, label: str = "adc", fsm_model: str = "spice",
                 ls_model: str = "spice"):
        self.ctx, self.cfg, self.lib = ctx, ctx.cfg, ctx.lib
        c = self.cfg
        self.variant = variant
        self.lib.closure(c.ADC_SUBCKT)          # raises early if FSM netlist missing
        from .domains import build
        tim = timing_from_results(c)
        c.LS_UP_DELAY_USED = c.LS_UP_DELAY or tim.get("ls_up_delay") or 0.7e-9
        c.LS_DOWN_DELAY_USED = c.LS_DOWN_DELAY or tim.get("ls_down_delay") or 0.25e-9
        direct = ls_model == "xspice" and fsm_model == "xspice"
        self.dom = build(c, self.lib, direct)   # 1.2 V FSM domain + level shifters (sets c.VDIG)
        self.sc = self.lib.get(self.dom.top)
        self.t_conv = t_conv or 2e-6
        self.t_sf_rel = t_sf_rel                # sampling-window end relative to START
        self.label = label
        n_rst = math.ceil(c.T_RSTN / c.TCLK) + 2
        self.t0 = (n_rst + c.START_PHASE) * c.TCLK
        self.bits = [b.lower() for b in c.CODE_BITS]
        self.dut = self.sc.name if variant == "real" else self.sc.name + "_idealsw"
        self.fsm_model = fsm_model
        self.overrides: dict[str, str] = {}
        self._xspice_text = None
        if fsm_model == "xspice":
            from .xspice_fsm import LibertyError, XspiceConverter
            conv = XspiceConverter(c, self.lib, c.STDCELL_LIB, c.XSPICE_GATE_DELAY, c.XSPICE_CLK2Q,
                                   c.XSPICE_TRF, vdd=self.dom.fsm_supply,
                                   hv_out=self.dom.up_ports if self.dom.mode == "generated_direct" else None,
                                   hv_in=self.dom.down_ports if self.dom.mode == "generated_direct" else None,
                                   vhv=c.VDD, up_delay=c.LS_UP_DELAY_USED, down_delay=c.LS_DOWN_DELAY_USED)
            try:
                self._xspice_text = conv.convert(c.FSM_SUBCKT)
            except (LibertyError, OSError) as e:
                print(f"  WARNING: XSPICE model of the FSM not possible ({e}); "
                      f"falling back to the transistor-level FSM (slow)")
                self.fsm_model = "spice"
                if self.dom.mode == "generated_direct":
                    self.dom = build(c, self.lib, False)
                    self.sc = self.lib.get(self.dom.top)
                    self.dut = self.sc.name if variant == "real" else self.sc.name + "_idealsw"

    # DUT
    def _ideal_subckt(self) -> str:
        c = self.cfg
        body = []
        top = {c.ADC_INTERNAL["vcp"].lower(), c.ADC_INTERNAL["vcn"].lower()}
        for line in self.sc.body:
            s = line.split()
            model = [t for t in s if "=" not in t][-1].lower() if s[0][0] in "xX" else ""
            if model in IDEALIZED:
                continue
            if s[0][0] in "xX" and model != "cdac_caps_10b_diff" and top & {t.lower() for t in s[1:]}:
                # comparator: drive its inputs through ideal buffers so its (nonlinear) input
                # capacitance and kickback do not load the CDAC - pure logic check of the FSM
                s = [t + "_ib" if t.lower() in top else t for t in s]
                line = " ".join(s)
            body.append(line)
        for n in top:
            body.append(f"Bib_{n} {n}_ib 0 V = V({n})")
        th = c.VDD / 2
        body += [
            "Ssp ainp vcp sample 0 swideal", "Ssn ainn vcn sample 0 swideal",
            f".model swideal sw vt={th} vh=0.05 ron=1 roff=1e14",
        ]
        for side in "pn":
            for i in range(c.NBITS):
                body.append(f"Bb{side}{i} b{side}{i} 0 V = V(vcm) + (V(vrefp)-V(vcm))"
                            f"*(0.5+0.5*tanh((V(db{side}{i})-{th})*40))")
        return "\n".join([f".subckt {self.dut} {' '.join(self.sc.ports)}", *body, f".ends {self.dut}"])

    # deck
    def t_start(self, j: int) -> float:
        return self.t0 + j * self.t_conv

    def deck(self, n_conv: int, dc_values=None, sine=None, save_internal=False,
             currents=False, save_step=None, title="adc") -> Deck:
        """dc_values: list (one DC differential input per conversion) or
        sine: dict(amp=diff peak, freq=Hz, phase_deg=)."""
        c = self.cfg
        d = Deck(c, self.lib, title)
        if self.variant == "real":
            d.use(self.sc.name)
        else:
            for inst, model in self.sc.instances:
                if model.lower() not in IDEALIZED:
                    d.use(model)
            d.add_subckt_text(self._ideal_subckt())
        if self._xspice_text:
            d.override(c.FSM_SUBCKT, self._xspice_text)
        for name, text in self.overrides.items():
            d.override(name, text)
        d.add(f"x1 {' '.join(self.sc.ports)} {self.dut}")
        # small loads on the digital outputs / exported comparator output (floating nodes otherwise)
        for p in self.sc.ports:
            if p.lower() in [b.lower() for b in c.CODE_BITS] + ["valid", "busy", "voutn"]:
                d.add(f"Cl_{p} {p} 0 10f")
        vd = self.dom.vdig                   # CLK/RSTN/START live in the FSM (1.2 V) domain
        P = c.ADC_PORTS
        d.add(f"Vclk {P['clk']} 0 PULSE(0 {vd} 0 {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} "
              f"{fmt(c.TCLK / 2 - c.T_EDGE)} {fmt(c.TCLK)})")
        d.add(f"Vrstn {P['rstn']} 0 PWL(0 0 {fmt(c.T_RSTN)} 0 {fmt(c.T_RSTN + c.T_EDGE)} {vd})")
        d.add(f"Vstart {P['start']} 0 PULSE(0 {vd} {fmt(self.t0)} {fmt(c.T_EDGE)} {fmt(c.T_EDGE)} "
              f"{fmt(c.START_WIDTH_CLK * c.TCLK - c.T_EDGE)} {fmt(self.t_conv)})")
        d.add(f"Vvdd vdd 0 {c.VDD}", "Vvss vss 0 0", f"Vvcm vcm 0 {c.VCM}", f"Vvref vrefp 0 {c.VREFP}")
        if self.dom.lv_port:
            d.add(f"Vvddlv {self.dom.lv_port} 0 {c.VDD_LV}")
        if sine is not None:
            a = sine["amp"] / 2
            d.add(f"Vainp ainp 0 SIN({c.VCM} {fmt(a)} {fmt(sine['freq'])} 0 0 {fmt(sine['phase_deg'])})",
                  f"Vainn ainn 0 SIN({c.VCM} {fmt(-a)} {fmt(sine['freq'])} 0 0 {fmt(sine['phase_deg'])})")
        else:
            vals = list(dc_values)
            pts_p, pts_n = [(0.0, c.VCM + vals[0] / 2)], [(0.0, c.VCM - vals[0] / 2)]
            for j in range(1, len(vals)):
                if self.t_sf_rel is not None:
                    tc = self.t_start(j - 1) + self.t_sf_rel + c.TCLK
                else:
                    tc = self.t_start(j - 1) + 0.5 * self.t_conv
                pts_p += [(tc, c.VCM + vals[j - 1] / 2), (tc + 0.2e-9, c.VCM + vals[j] / 2)]
                pts_n += [(tc, c.VCM - vals[j - 1] / 2), (tc + 0.2e-9, c.VCM - vals[j] / 2)]
            d.add(f"Vainp ainp 0 {pwl(pts_p)}", f"Vainn ainn 0 {pwl(pts_n)}")
        vecs = [f"v({P['valid']})", f"v({P['busy']})", f"v({P['start']})"] + [f"v({b})" for b in self.bits]
        if save_internal:
            ai = c.ADC_INTERNAL
            vecs += [f"v(x1.{ai['sample']})", f"v(x1.{ai['comp_clk']})", f"v(x1.{ai['vcp']})",
                     f"v(x1.{ai['vcn']})", f"v(x1.{ai['voutp']})", "v(ainp)", "v(ainn)"]
            vecs += [f"v(x1.dbp{i})" for i in range(c.NBITS)] + [f"v(x1.dbn{i})" for i in range(c.NBITS)]
            if self.dom.mode == "generated":      # both sides of the level shifters
                vecs += [f"v(x1.{n}_lv)" for n in (ai["sample"], ai["comp_clk"], ai["voutp"])
                         if n in self.dom.up + self.dom.down]
        if currents:
            # charge integrators (exact simulator integration of each supply current):
            # V(q_x) = (1/1nF) * integral I(Vx) dt
            srcs = ["vvdd", "vvref", "vvcm"] + (["vvddlv"] if self.dom.lv_port else [])
            for src in srcs:
                d.add(f"Fq_{src} 0 q_{src} {src} 1", f"Cq_{src} q_{src} 0 1n", f"Rq_{src} q_{src} 0 1e15")
            vecs += [f"v(q_{src})" for src in srcs]
        save_step = save_step or c.ADC_SAVE_STEP
        # NOTE: no `.options interp` - with XSPICE + floating CDAC top plates it corrupted data
        d.add(".save " + " ".join(vecs))
        tstop = self.t_start(n_conv) + c.READ_DELAY + 2 * c.TCLK
        d.control(f"tran {fmt(save_step)} {fmt(tstop)} 0 {fmt(c.ADC_TSTEP)}")
        d.wrdata("adc.txt", vecs)
        self.vecs = vecs
        return d

    #  parse
    def parse(self, res, n_conv: int) -> list[dict]:
        c = self.cfg
        dat = res.data("adc.txt")
        t = dat["t"]
        vt = self.dom.vdig / 2                # code / valid are in the FSM domain
        edges = wave.crossings(t, dat[f"v({c.ADC_PORTS['valid']})"], vt, "rise")
        out = []
        for j in range(n_conv):
            ts = self.t_start(j)
            e = edges[(edges > ts) & (edges <= ts + self.t_conv)]
            if len(e) == 0:
                out.append({"code": -1, "t_valid": float("nan"), "latency": float("nan"), "n_valid": 0})
                continue
            tr = e[0] + c.READ_DELAY
            code = 0
            for b in self.bits:
                code = (code << 1) | int(wave.sample_after(t, dat[f"v({b})"], tr) > vt)
            out.append({"code": code, "t_valid": float(e[0]), "latency": float(e[0] - ts),
                        "n_valid": int(len(e))})
        return out

    # high level
    def convert(self, values, label: str, run_dir: str, chunk: int | None = None) -> np.ndarray:
        """Convert DC differential inputs; returns codes (-1 = no valid)."""
        c = self.cfg
        values = list(values)
        chunk = chunk or max(4, min(c.ADC_CHUNK, math.ceil(len(values) / max(1, c.JOBS))))
        w = c.ADC_WARMUP
        jobs, spans = [], []
        for k in range(0, len(values), chunk):
            part = values[k:k + chunk]
            vals = [part[0]] * w + part
            d = self.deck(len(vals), dc_values=vals, title=f"{label} chunk {k // chunk}")
            jobs.append((d, f"{label}_{k // chunk:03d}"))
            spans.append((len(vals), len(part)))
        res = run_many(c, jobs, run_dir, label, allow_fail=True)
        codes = []
        for r, (n_all, n_part) in zip(res, spans):
            if r is None:                     # aborted chunk ( metastable comparator)
                codes += [-1] * n_part
            else:
                codes += [p["code"] for p in self.parse(r, n_all)[w:w + n_part]]
        return np.array(codes)

    def convert_sine(self, n: int, amp: float, fin: float, label: str, run_dir: str,
                     chunk: int | None = None, t_sample_rel: float | None = None) -> np.ndarray:
        """n conversions of a continuous differential sine (coherent if fin=M*fs/n)."""
        c = self.cfg
        chunk = chunk or max(4, min(c.ADC_CHUNK, math.ceil(n / max(1, c.JOBS))))
        w = c.ADC_WARMUP
        jobs, spans = [], []
        for k in range(0, n, chunk):
            m = min(chunk, n - k)
            # global sampling time of conversion g: g*Tc + t_rel ; local j - global k - w + j
            shift = (k - w) * self.t_conv - self.t0
            ph = (360.0 * fin * shift) % 360.0
            d = self.deck(w + m, sine={"amp": amp, "freq": fin, "phase_deg": ph},
                          title=f"{label} chunk {k // chunk}")
            jobs.append((d, f"{label}_{k // chunk:03d}"))
            spans.append((w + m, m))
        res = run_many(c, jobs, run_dir, label, allow_fail=True)
        codes = []
        for r, (n_all, m) in zip(res, spans):
            if r is None:
                codes += [-1] * m
            else:
                codes += [p["code"] for p in self.parse(r, n_all)[w:w + m]]
        return np.array(codes)

    def ideal_code(self, v):
        c = self.cfg
        return np.clip(np.floor((np.asarray(v) + c.VFS / 2) / c.LSB), 0, c.NCODES - 1).astype(int)


def timing_from_results(cfg) -> dict:
    import json
    p = os.path.join(cfg.RESULTS_DIR, "adc_timing", "summary.json")
    try:
        with open(p) as f:
            return json.load(f)["data"]["timing"]
    except (OSError, KeyError, ValueError):
        return {}


def cdac_mismatch_text(lib, cfg, sigma_unit: float, seed: int) -> tuple[str, dict]:
    """cdac_caps_10b_diff with random capacitor values (sigma_unit = relative sigma of one Cu;
    a cap of m units gets sigma_unit/sqrt(m))."""
    import re
    rng = np.random.default_rng(seed)
    sc = lib.get("cdac_caps_10b_diff")
    body, vals = [], {}
    for line in sc.body:
        m = re.match(r"^(C\S+)\s+(\S+)\s+(\S+)\s+\{\s*([\d.]+)\s*\*\s*Cu\s*\}", line, re.I)
        if m:
            units = float(m.group(4))
            f = 1 + sigma_unit / math.sqrt(units) * rng.standard_normal()
            body.append(f"{m.group(1)} {m.group(2)} {m.group(3)} {{{units}*Cu*{f:.8f}}}")
            vals[f"{m.group(2)}-{m.group(3)}"] = units * f
        else:
            body.append(line)
    text = "\n".join([f".subckt {sc.name} {' '.join(sc.ports)}", *body, f".ends {sc.name}"])
    return text, vals
