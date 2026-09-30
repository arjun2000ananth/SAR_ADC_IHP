"""
Convert a gate-level (std-cell) SPICE netlist into an XSPICE digital model.

The logic of every std-cell is taken from its Liberty `function` / `ff` / `latch` groups, so the converted model is logic-equivalent to the synthesized netlist.
Analog <-> digital boundaries get adc_bridge / dac_bridge elements.  Running the full ADC with this model is ~10-50x faster than simulating ~3000 PSP transistors of the FSM, while comparator, switches and CDAC stay transistor-level.
"""
from __future__ import annotations

import re

STD_PREFIX = ("sg13cmos5l_", "sg13g2_")


class LibertyError(RuntimeError):
    pass
# Liberty reader (only what we need)

def _group_end(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise LibertyError("unbalanced braces")


def read_liberty(path: str, wanted: set[str]) -> dict:
    with open(path, errors="replace") as f:
        text = f.read()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = text.replace("\\\n", " ")
    cells = {}
    for m in re.finditer(r"\bcell\s*\(\s*\"?([\w]+)\"?\s*\)\s*\{", text):
        name = m.group(1)
        if name.lower() not in wanted:
            continue
        end = _group_end(text, m.end() - 1)
        body = text[m.end():end]
        info = {"pins": {}, "ff": None, "latch": None}
        for pm in re.finditer(r"(?<![\w_])pin\s*\(\s*\"?([\w\[\]]+)\"?\s*\)\s*\{", body):
            pend = _group_end(body, pm.end() - 1)
            pbody = body[pm.end():pend]
            # only top-level attributes of the pin
            top = re.sub(r"\{[^{}]*\}", "", pbody)
            while re.search(r"\{[^{}]*\}", top):
                top = re.sub(r"\{[^{}]*\}", "", top)
            dm = re.search(r"direction\s*:\s*\"?(\w+)\"?", top)
            fm = re.search(r"function\s*:\s*\"([^\"]*)\"", top)
            info["pins"][pm.group(1)] = {"dir": dm.group(1) if dm else "", "function": fm.group(1) if fm else None,
                                        "three_state": "three_state" in top}
        for kind in ("ff", "latch"):
            gm = re.search(kind + r"\s*\(\s*\"?(\w+)\"?\s*,\s*\"?(\w+)\"?\s*\)\s*\{([^{}]*)\}", body)
            if gm:
                attrs = dict((k, v) for k, v in re.findall(r"(\w+)\s*:\s*\"([^\"]*)\"", gm.group(3)))
                info[kind] = {"q": gm.group(1), "qn": gm.group(2), **attrs}
        if "statetable" in body:
            info["statetable"] = True
        cells[name.lower()] = info
    missing = wanted - set(cells)
    if missing:
        raise LibertyError(f"cells not found in {path}: {sorted(missing)}")
    return cells

# Bolean expressions (Liberty syntax)

_TOK = re.compile(r"\s*(\(|\)|!|'|\*|&|\+|\||\^|[A-Za-z_][\w\[\]]*|[01])")


def _tokens(expr: str):
    pos, out = 0, []
    expr = expr.strip()
    while pos < len(expr):
        m = _TOK.match(expr, pos)
        if not m:
            if expr[pos].isspace():
                pos += 1
                continue
            raise LibertyError(f"cannot parse function '{expr}' at {expr[pos:]}")
        out.append(m.group(1))
        pos = m.end()
    return out


class Expr:
    def __init__(self, text: str):
        self.text = text
        self.toks = _tokens(text)
        self.i = 0
        self.tree = self._or()
        if self.i != len(self.toks):
            raise LibertyError(f"trailing tokens in '{text}'")

    def _peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _next(self):
        t = self._peek()
        self.i += 1
        return t

    def _or(self):
        n = self._and()
        while self._peek() in ("+", "|"):
            self._next()
            n = ("or", n, self._and())
        return n

    def _and(self):
        n = self._xor()
        while True:
            t = self._peek()
            if t in ("*", "&"):
                self._next()
                n = ("and", n, self._xor())
            elif t is not None and (t == "(" or t == "!" or re.match(r"[A-Za-z_01]", t)):
                n = ("and", n, self._xor())       # juxtaposition = AND
            else:
                return n

    def _xor(self):
        n = self._unary()
        while self._peek() == "^":
            self._next()
            n = ("xor", n, self._unary())
        return n

    def _unary(self):
        if self._peek() == "!":
            self._next()
            return ("not", self._unary())
        n = self._atom()
        while self._peek() == "'":
            self._next()
            n = ("not", n)
        return n

    def _atom(self):
        t = self._next()
        if t == "(":
            n = self._or()
            if self._next() != ")":
                raise LibertyError(f"missing ) in '{self.text}'")
            return n
        if t in ("0", "1"):
            return ("const", int(t))
        if t is None or not re.match(r"[A-Za-z_]", t):
            raise LibertyError(f"unexpected token {t!r} in '{self.text}'")
        return ("var", t)

    def vars(self):
        out = []

        def walk(n):
            if n[0] == "var":
                if n[1] not in out:
                    out.append(n[1])
            elif n[0] != "const":
                for c in n[1:]:
                    walk(c)
        walk(self.tree)
        return out

    def eval(self, env):
        def ev(n):
            k = n[0]
            if k == "var":
                return env[n[1]]
            if k == "const":
                return n[1]
            if k == "not":
                return 1 - ev(n[1])
            a, b = ev(n[1]), ev(n[2])
            return {"and": a & b, "or": a | b, "xor": a ^ b}[k]
        return ev(self.tree)

    def table(self, order):
        vals = []
        for idx in range(2 ** len(order)):
            env = {v: (idx >> i) & 1 for i, v in enumerate(order)}
            vals.append(str(self.eval(env)))
        return "".join(vals)

# Converter
class XspiceConverter:
    def __init__(self, cfg, lib, liberty: str, gate_delay=50e-12, clk2q=100e-12, trf=100e-12,
                 cin=5e-15, vdd=None, hv_out=None, hv_in=None, vhv=None, up_delay=0.7e-9,
                 down_delay=0.25e-9):
        """hv_out / hv_in: FSM ports whose bridges also do the 1.2<->3.3 V level shifting
        (used instead of transistor-level shifters in long ADC runs)."""
        self.vdd = vdd
        self.hv_out = {p.lower() for p in (hv_out or [])}
        self.hv_in = {p.lower() for p in (hv_in or [])}
        self.vhv = vhv
        self.up_delay, self.down_delay = up_delay, down_delay
        self.cfg, self.lib = cfg, lib
        self.liberty = liberty
        self.gd, self.cq, self.trf, self.cin = gate_delay, clk2q, trf, cin
        self.models: dict[str, str] = {}

    def _model(self, kind: str, **params) -> str:
        key = kind + "_" + "_".join(f"{k}{v}" for k, v in sorted(params.items()))
        import hashlib
        name = f"xm_{kind}_" + hashlib.md5(key.encode()).hexdigest()[:10]
        if name not in self.models:
            ps = " ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v:g}" for k, v in params.items())
            self.models[name] = f".model {name} {kind}({ps})"
        return name

    def convert(self, top: str) -> str:
        c = self.cfg
        subs = self.lib.closure(top)
        std = set()
        for sc in subs:
            for _, m in sc.instances:
                if m.lower().startswith(STD_PREFIX):
                    std.add(m.lower())
        self.cells = read_liberty(self.liberty, std)
        self.spice_ports = self._stdcell_ports(std)
        out = []
        for sc in subs:
            out.append(self._convert_subckt(sc))
        vdd = self.vdd if self.vdd is not None else getattr(c, "VDIG", c.VDD)   # FSM supply (1.2 V domain)
        hdr = [
            f".model xm_adc adc_bridge(in_low={0.45 * vdd:g} in_high={0.55 * vdd:g} rise_delay=1e-12 fall_delay=1e-12)",
            f".model xm_dac dac_bridge(out_low=0 out_high={vdd:g} out_undef={vdd / 2:g} "
            f"t_rise={self.trf:g} t_fall={self.trf:g})",
            ".model xm_pu d_pullup(load=1e-15)", ".model xm_pd d_pulldown(load=1e-15)",
        ]
        if self.hv_out or self.hv_in:
            vh = self.vhv or c.VDD
            hdr += [
                f".model xm_dac_hv dac_bridge(out_low=0 out_high={vh:g} out_undef={vh / 2:g} "
                f"t_rise={self.trf:g} t_fall={self.trf:g})",
                f".model xm_adc_hv adc_bridge(in_low={0.45 * vh:g} in_high={0.55 * vh:g} "
                f"rise_delay={self.down_delay:g} fall_delay={self.down_delay:g})",
                f".model xm_lsdly d_buffer(rise_delay={self.up_delay:g} fall_delay={self.up_delay:g} "
                f"input_load=1e-15)",
            ]
        return "\n".join(["* XSPICE digital model generated by sartb.xspice_fsm", *hdr,
                          *self.models.values(), *out])

    def _stdcell_ports(self, std):
        import os
        ports = {}
        path = self.cfg.STDCELL_SPICE
        if not os.path.isfile(path):
            raise LibertyError(f"STDCELL_SPICE not found: {path}")
        with open(path) as f:
            for line in f:
                m = re.match(r"\s*\.subckt\s+(\S+)\s+(.*)", line, re.I)
                if m and m.group(1).lower() in std:
                    ports[m.group(1).lower()] = m.group(2).split()
        return ports

    def _convert_subckt(self, sc) -> str:
        lines = []
        # classify nets
        std_inst, other = [], []
        for line in sc.body:
            s = line.split()
            if s and s[0][0] in "xX":
                model = [t for t in s if "=" not in t][-1]
                if model.lower().startswith(STD_PREFIX):
                    std_inst.append((s[0], [t for t in s[1:] if "=" not in t][:-1], model.lower()))
                    continue
            other.append(line)
        if not std_inst:
            return sc.text()
        dig_driven, dig_read = set(), set()
        conns = []
        for inst, nets, model in std_inst:
            ports = self.spice_ports[model]
            if len(ports) != len(nets):
                raise LibertyError(f"{inst}: {model} expects {len(ports)} nets, got {len(nets)}")
            pmap = dict(zip(ports, nets))
            conns.append((inst, model, pmap))
            cell = self.cells[model]
            for p, n in pmap.items():
                if p.upper() in ("VDD", "VSS", "VPWR", "VGND"):
                    continue
                d = cell["pins"].get(p, {}).get("dir", "")
                if d == "output":
                    dig_driven.add(n.lower())
                elif d == "input":
                    dig_read.add(n.lower())
        analog = {p.lower() for p in sc.ports}
        for line in other:
            for t in line.split()[1:]:
                if "=" not in t:
                    analog.add(t.lower())
        supplies = {"0", "gnd", "vdd", "vss", "vpwr", "vgnd"}

        def dnet(n):
            n = n.lower()
            return f"d_{n}" if n in analog else n

        # bridges
        a_in = sorted(n for n in dig_read if n in analog and n not in dig_driven and n not in supplies)
        a_out = sorted(n for n in dig_driven if n in analog)
        top_ports = {p.lower() for p in sc.ports}
        h_in = [n for n in a_in if n in self.hv_in and n in top_ports]
        h_out = [n for n in a_out if n in self.hv_out and n in top_ports]
        a_in = [n for n in a_in if n not in h_in]
        a_out = [n for n in a_out if n not in h_out]
        if a_in:
            lines.append(f"abr_in [{' '.join(a_in)}] [{' '.join('d_' + n for n in a_in)}] xm_adc")
            lines += [f"Cbr_{n} {n} 0 {self.cin:g}" for n in a_in]
        if a_out:
            lines.append(f"abr_out [{' '.join('d_' + n for n in a_out)}] [{' '.join(a_out)}] xm_dac")
        if h_in:      # 3.3 V input, thresholds at VDD/2, down-shifter delay
            lines.append(f"abr_hvin [{' '.join(h_in)}] [{' '.join('d_' + n for n in h_in)}] xm_adc_hv")
            lines += [f"Cbr_{n} {n} 0 {self.cin:g}" for n in h_in]
        if h_out:     # up-shifter: pure delay, then a 0..VDD output
            for n in h_out:
                lines.append(f"alsd_{n} d_{n} d_{n}_ls xm_lsdly")
            lines.append(f"abr_hvout [{' '.join(f'd_{n}_ls' for n in h_out)}] [{' '.join(h_out)}] xm_dac_hv")
        consts = {}

        def const(v):
            if v not in consts:
                consts[v] = f"dconst{v}"
                lines.append(f"a_const{v} dconst{v} {'xm_pu' if v else 'xm_pd'}")
            return consts[v]

        # cells
        for inst, model, pmap in conns:
            cell = self.cells[model]
            iname = re.sub(r"[^\w]", "_", inst)
            local = {p: dnet(n) for p, n in pmap.items()}

            def sig(expr_text, tag):
                """digital net for an expression over the cell's pins (+ internal IQ/IQN)."""
                e = Expr(expr_text)
                vs = e.vars()
                if not vs:
                    return const(e.eval({}))
                if len(vs) == 1 and e.table(vs) == "01":
                    return local[vs[0]]
                out = f"{iname}_{tag}"
                tbl = e.table(vs)
                m = self._model("d_lut", rise_delay=self.gd, fall_delay=self.gd, input_load=1e-15,
                                table_values=tbl)
                lines.append(f"a{iname}_{tag} [{' '.join(local[v] for v in vs)}] {out} {m}")
                return out

            seq = cell["ff"] or cell["latch"]
            if cell.get("statetable") and not seq:
                raise LibertyError(f"{model}: statetable cells are not supported")
            if seq:
                q, qn = seq["q"], seq["qn"]
                local[q], local[qn] = f"{iname}_{q}", f"{iname}_{qn}"
                if cell["ff"]:
                    data = sig(seq["next_state"], "d")
                    clk = sig(seq["clocked_on"], "clk")
                    en = None
                else:
                    data = sig(seq["data_in"], "d")
                    en = sig(seq["enable"], "en")
                setn = sig(seq["preset"], "set") if "preset" in seq else "NULL"
                rstn = sig(seq["clear"], "rst") if "clear" in seq else "NULL"
                if cell["ff"]:
                    m = self._model("d_dff", clk_delay=self.cq, set_delay=self.cq, reset_delay=self.cq,
                                    rise_delay=1e-12, fall_delay=1e-12, ic=0)
                    lines.append(f"a{iname}_ff {data} {clk} {setn} {rstn} {local[q]} {local[qn]} {m}")
                else:
                    m = self._model("d_dlatch", data_delay=self.cq, enable_delay=self.cq, set_delay=self.cq,
                                    reset_delay=self.cq, rise_delay=1e-12, fall_delay=1e-12, ic=0)
                    lines.append(f"a{iname}_lat {data} {en} {setn} {rstn} {local[q]} {local[qn]} {m}")
            for p, pin in cell["pins"].items():
                if pin["dir"] != "output" or p not in pmap:
                    continue
                if pin["three_state"]:
                    raise LibertyError(f"{model}: tri-state outputs are not supported")
                if pin["function"] is None:
                    raise LibertyError(f"{model}.{p}: no function")
                target = local[p]
                fn = pin["function"].strip()
                if seq and fn in (seq["q"], seq["qn"]):
                    src = local[fn]
                    # connect internal state net to the output net via a buffer LUT
                    m = self._model("d_lut", rise_delay=1e-12, fall_delay=1e-12, input_load=1e-15,
                                    table_values="01")
                    lines.append(f"a{iname}_{p}_buf [{src}] {target} {m}")
                    continue
                e = Expr(fn)
                vs = e.vars()
                if not vs:
                    lines.append(f"a{iname}_{p} {target} {'xm_pu' if e.eval({}) else 'xm_pd'}")
                    continue
                m = self._model("d_lut", rise_delay=self.gd, fall_delay=self.gd, input_load=1e-15,
                                table_values=e.table(vs))
                lines.append(f"a{iname}_{p} [{' '.join(local[v] for v in vs)}] {target} {m}")
        head = f".subckt {sc.name} {' '.join(sc.ports)}" + (f" {sc.params}" if sc.params else "")
        return "\n".join([f"* {sc.name}: {len(conns)} std-cells -> XSPICE", head, *other, *lines,
                          f".ends {sc.name}"])
