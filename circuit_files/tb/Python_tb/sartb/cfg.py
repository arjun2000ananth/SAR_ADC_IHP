"""Configuration loading: config.py + --set overrides + derived quantities."""
from __future__ import annotations

import ast
import importlib.util
import os
from types import SimpleNamespace

_TEMPLATE_KEYS = ("HERE", "PDK_ROOT", "PDK", "FSM_NETLIST")


def _expand(value, env):
    if isinstance(value, str):
        # expand repeatedly so {FSM_NETLIST} -> "{HERE}/..." -> absolute
        for _ in range(4):
            try:
                new = value.format(**env)
            except (KeyError, IndexError, ValueError):
                return value
            if new == value:
                break
            value = new
        return os.path.expanduser(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_expand(v, env) for v in value)
    if isinstance(value, dict):
        return {k: _expand(v, env) for k, v in value.items()}
    return value


def _parse_value(text: str):
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def load(path: str | None = None, overrides: list[str] | None = None) -> SimpleNamespace:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = path or os.path.join(here, "config.py")
    spec = importlib.util.spec_from_file_location("sartb_user_config", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = {k: getattr(mod, k) for k in dir(mod) if k.isupper()}
    for item in overrides or []:
        if "=" not in item:
            raise SystemExit(f"--set expects NAME=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        if k.startswith("SPEC."):
            raw.setdefault("SPEC", {})[k[5:]] = _parse_value(v)
        else:
            raw[k] = _parse_value(v)
    raw.setdefault("HERE", here)

    env = {k: raw.get(k, "") for k in _TEMPLATE_KEYS}
    for _ in range(3):
        env = {k: _expand(v, env) for k, v in env.items()}
    cfg = {k: _expand(v, env) for k, v in raw.items()}
    c = SimpleNamespace(**cfg)

    # Dervied
    c.TCLK = 1.0 / c.FCLK
    c.VFS = c.VFS_DIFF if c.VFS_DIFF else 2.0 * (c.VREFP - c.VCM)
    c.NCODES = 2 ** c.NBITS
    c.LSB = c.VFS / c.NCODES
    # digital swing of CLK/RSTN/START and the code outputs (refined by sartb.domains.build)
    c.VDIG = c.VDD_LV if getattr(c, "FSM_DOMAIN", "lv") == "lv" else c.VDD
    c.CONFIG_PATH = os.path.abspath(path)
    return c


def describe(c) -> str:
    return (f"corner={c.CORNER} T={c.TEMP}C VDD={c.VDD} VDD_LV={c.VDD_LV} VREFP={c.VREFP} VCM={c.VCM} "
            f"Cu={c.CU*1e15:.3g}f  FS(diff)={c.VFS:.4g}Vpp  LSB={c.LSB*1e3:.4g}mV  "
            f"FCLK={c.FCLK/1e6:.4g}MHz")
