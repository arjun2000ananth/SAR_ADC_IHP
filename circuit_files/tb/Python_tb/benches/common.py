"""Shared helpers for the benches."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402,F401

from sartb.spice import Deck  # noqa: E402

ROLE_PATTERNS = {
    "outp": [r"^v?outp$", r"^outp"],
    "outn": [r"^v?outn$", r"^outn"],
    "inp": [r"^v?inp$", r"^inp"],
    "inn": [r"^v?inn$", r"^inn"],
    "clk": [r"clk"],
    "vdd": [r"^vdd"],
    "vss": [r"^vss", r"^gnd$"],
}


def map_pins(subckt, roles: list[str], override: str | None = None) -> dict[str, str]:
    """Map roles -> actual port names by regex on port names (override: 'role=Port,...')."""
    out: dict[str, str] = {}
    if override:
        for item in override.split(","):
            r, p = item.split("=")
            out[r.strip()] = p.strip()
    for role in roles:
        if role in out:
            continue
        for pat in ROLE_PATTERNS.get(role, [role]):
            hits = [p for p in subckt.ports if re.search(pat, p, re.I)]
            if len(hits) == 1:
                out[role] = hits[0]
                break
        if role not in out:
            raise SystemExit(f"cannot map role '{role}' on {subckt.name} ports {subckt.ports}; "
                             f"use --pins {role}=PORT")
    return out


def instance_line(inst: str, subckt, net_of_port: dict[str, str]) -> str:
    """x-line with nets in the subckt's port order; unmapped ports get unique nets."""
    nets = [net_of_port.get(p, f"nc_{inst}_{p}") for p in subckt.ports]
    return f"{inst} {' '.join(nets)} {subckt.name}"


def deck(ctx, title: str, **kw) -> Deck:
    return Deck(ctx.cfg, ctx.lib, title, **kw)


def run_dir(ctx, sub: str = "") -> str:
    d = os.path.join(ctx.out_dir, "runs", sub) if sub else os.path.join(ctx.out_dir, "runs")
    os.makedirs(d, exist_ok=True)
    return d


def ctx_ns(**kw) -> SimpleNamespace:
    return SimpleNamespace(**kw)


def adc_timing(cfg) -> dict:
    """Timing measured by the adc_timing bench (sampling window etc.), or {}."""
    import json
    p = os.path.join(cfg.RESULTS_DIR, "adc_timing", "summary.json")
    try:
        with open(p) as f:
            return json.load(f).get("data", {}).get("timing", {})
    except (OSError, ValueError):
        return {}


def sampling_window(cfg) -> tuple[float, str]:
    """(T_sample, where it came from)."""
    if getattr(cfg, "T_SAMPLE", None):
        return float(cfg.T_SAMPLE), "config T_SAMPLE"
    t = adc_timing(cfg)
    if t.get("t_sample"):
        return float(t["t_sample"]), "adc_timing bench"
    return 0.25 / cfg.FS_TARGET, "default 0.25/FS_TARGET (run adc_timing to use the real window)"


def dac_window(cfg) -> tuple[float, str]:
    """Settling budget for one DAC step: comp_clk low time measured by adc_timing, else 1 CLK."""
    t = adc_timing(cfg)
    if t.get("t_dac"):
        return float(t["t_dac"]), "comp_clk low time (adc_timing)"
    return cfg.TCLK, "1 CLK period (run adc_timing for the FSM's real budget)"


def conv_period(cfg) -> tuple[float, str]:
    t = adc_timing(cfg)
    if cfg.CONV_PERIOD_CLK:
        return cfg.CONV_PERIOD_CLK * cfg.TCLK, "config CONV_PERIOD_CLK"
    if t.get("t_conv_period"):
        return float(t["t_conv_period"]), "adc_timing bench"
    return 1.0 / cfg.FS_TARGET, "1/FS_TARGET"


def ensure_timing(ctx) -> dict:
    """adc_timing results; runs the adc_timing bench first if they do not exist yet."""
    t = adc_timing(ctx.cfg)
    if t:
        return t
    import argparse
    import types
    from sartb.report import Report
    from . import adc_timing as at
    print("  (no adc_timing results yet -> running adc_timing first)")
    sub = types.SimpleNamespace()
    sub.cfg, sub.lib = ctx.cfg, ctx.lib
    sub.out_dir = os.path.join(ctx.cfg.RESULTS_DIR, "adc_timing")
    sub.rep = Report("adc_timing", sub.out_dir, ctx.cfg)
    p = argparse.ArgumentParser()
    at.add_args(p)
    args = p.parse_args([])
    args.quick = False
    at.run(sub, args)
    sub.rep.save()
    print(sub.rep.table())
    return adc_timing(ctx.cfg)
