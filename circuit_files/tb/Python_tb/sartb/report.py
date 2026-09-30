"""Result collection, PASS/FAIL checks and summary files."""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np


def eng(x, unit: str = "", digits: int = 4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x))
    if not isinstance(x, (int, float, np.floating, np.integer)):
        return str(x)
    x = float(x)
    if unit and unit not in ("dB", "dBc", "dBFS", "%", "x", "deg") and abs(x) < 1e-15:
        x = 0.0
    if unit == "LSB" and abs(x) < 1e-6:
        x = 0.0
    if x == 0 or not unit or unit in ("dB", "dBc", "dBFS", "LSB", "%", "bits", "codes", "x", "deg"):
        return f"{x:.{digits}g}" + (f" {unit}" if unit else "")
    exp = int(math.floor(math.log10(abs(x)) / 3) * 3)
    exp = max(-15, min(12, exp))
    pre = {-15: "f", -12: "p", -9: "n", -6: "u", -3: "m", 0: "", 3: "k", 6: "M", 9: "G", 12: "T"}[exp]
    return f"{x / 10 ** exp:.{digits}g} {pre}{unit}"


class Report:
    def __init__(self, bench: str, out_dir: str, cfg):
        self.bench, self.out_dir, self.cfg = bench, out_dir, cfg
        self.rows: list[dict] = []
        self.notes: list[str] = []
        self.plots: list[str] = []
        self.data: dict = {}
        self.t0 = time.time()
        os.makedirs(out_dir, exist_ok=True)

    def add(self, key: str, value, unit: str = "", limit=None, cmp: str = "<=", desc: str = ""):
        """Record a metric. limit+cmp -> PASS/FAIL ('<=', '>=', 'abs<=', 'range')."""
        status = ""
        if limit is not None and value is not None and not (isinstance(value, float) and math.isnan(value)):
            v = float(value)
            if cmp == "<=":
                ok = v <= limit
            elif cmp == ">=":
                ok = v >= limit
            elif cmp == "abs<=":
                ok = abs(v) <= limit
            elif cmp == "range":
                ok = limit[0] <= v <= limit[1]
            elif cmp == "==":
                ok = v == limit
            elif cmp == "warn-range":
                ok = limit[0] <= v <= limit[1]
            else:
                raise ValueError(cmp)
            status = "PASS" if ok else ("WARN" if cmp.startswith("warn") else "FAIL")
        elif limit is not None:
            status = "FAIL"
        self.rows.append({"key": key, "value": value, "unit": unit, "limit": limit, "cmp": cmp,
                          "status": status, "desc": desc})
        return status

    def note(self, text: str):
        self.notes.append(text)
        print(f"  note: {text}")

    def plot(self, fig, name: str):
        path = os.path.join(self.out_dir, name)
        fig.savefig(path, dpi=130, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)
        self.plots.append(path)
        return path

    @property
    def passed(self) -> bool:
        return all(r["status"] != "FAIL" for r in self.rows)

    def _limit_str(self, r):
        if r["limit"] is None:
            return ""
        lim = r["limit"]
        if r["cmp"] in ("range", "warn-range"):
            return f"[{eng(lim[0], r['unit'])}, {eng(lim[1], r['unit'])}]"
        sym = {"<=": "<=", ">=": ">=", "abs<=": "|x|<=", "==": "=="}.get(r["cmp"], r["cmp"])
        return f"{sym} {eng(lim, r['unit'])}"

    def table(self) -> str:
        w = max([len(r["key"]) for r in self.rows] + [10])
        lines = [f"{'metric':<{w}}  {'value':>14}  {'spec':>16}  status"]
        lines.append("-" * len(lines[0]))
        for r in self.rows:
            lines.append(f"{r['key']:<{w}}  {eng(r['value'], r['unit']):>14}  "
                         f"{self._limit_str(r):>16}  {r['status']}")
        return "\n".join(lines)

    def save(self):
        def js(v):
            if isinstance(v, (np.floating, np.integer)):
                return v.item()
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, (np.bool_,)):
                return bool(v)
            return v

        summary = {
            "bench": self.bench, "passed": self.passed, "elapsed_s": time.time() - self.t0,
            "corner": self.cfg.CORNER, "temp": self.cfg.TEMP, "vdd": self.cfg.VDD,
            "metrics": [{k: js(v) for k, v in r.items()} for r in self.rows],
            "notes": self.notes, "plots": [os.path.basename(p) for p in self.plots],
            "data": json.loads(json.dumps(self.data, default=js)),
        }
        with open(os.path.join(self.out_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1, default=js)
        md = [f"# {self.bench}", "",
              f"corner `{self.cfg.CORNER}`, T = {self.cfg.TEMP} C, VDD = {self.cfg.VDD} V  —  "
              f"{'PASS' if self.passed else 'FAIL'}  ({summary['elapsed_s']:.0f} s)", "",
              "| metric | value | spec | status |", "|---|---|---|---|"]
        for r in self.rows:
            md.append(f"| {r['key']} | {eng(r['value'], r['unit'])} | {self._limit_str(r)} | {r['status']} |")
        if self.notes:
            md += ["", "## Notes", ""] + [f"- {n}" for n in self.notes]
        if self.plots:
            md += ["", "## Plots", ""] + [f"![{os.path.basename(p)}]({os.path.basename(p)})" for p in self.plots]
        with open(os.path.join(self.out_dir, "summary.md"), "w") as f:
            f.write("\n".join(md) + "\n")
        return summary
