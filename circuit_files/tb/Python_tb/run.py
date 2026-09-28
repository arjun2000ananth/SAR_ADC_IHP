#!/usr/bin/env python3
"""
SAR ADC Python testbench runer.

    python run.py list
    python run.py comparator                       # one bench
    python run.py comparator --dut simple_comparator
    python run.py blocks                           # every block bench
    python run.py adc                              # adc_timing + adc_static + adc_dynamic
    python run.py all
    python run.py selftest                         # full-ADC flow with the bundled reference FSM
    python run.py comparator --pvt --corners tt,ss,ff --temps -40,27,125
Common options: --config FILE  --set NAME=VALUE  --corner C  --temp T  --jobs N  --tag NAME
"""
from __future__ import annotations

import argparse
import csv
import importlib
import itertools
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sartb import cfg as cfgmod  # noqa: E402
from sartb.netlist import NetlistError, load_library  # noqa: E402
from sartb.report import Report  # noqa: E402
from sartb.spice import SimError  # noqa: E402

BENCHES = {
    # name            module                     needs FSM netlist
    "comparator":      ("benches.comparator", False),
    "sampling_switch": ("benches.sampling_switch", False),
    "inverter":        ("benches.inverter", False),
    "dac_switch":      ("benches.dac_switch", False),
    "cdac":            ("benches.cdac", False),
    "level_shifter":   ("benches.level_shifter", False),
    "cap_drivers":     ("benches.cap_drivers", False),
    "fsm":             ("benches.fsm", True),
    "adc_timing":      ("benches.adc_timing", True),
    "adc_static":      ("benches.adc_static", True),
    "adc_dynamic":     ("benches.adc_dynamic", True),
}
GROUPS = {
    "blocks": ["comparator", "sampling_switch", "inverter", "dac_switch", "cdac",
               "level_shifter", "cap_drivers"],
    "adc": ["adc_timing", "adc_static", "adc_dynamic"],
}
GROUPS["all"] = GROUPS["blocks"] + ["fsm"] + GROUPS["adc"]


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bench", help="bench name, group (blocks/adc/all) or 'list'")
    p.add_argument("--config", default=None)
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--corner", default=None)
    p.add_argument("--temp", type=float, default=None)
    p.add_argument("--vdd", type=float, default=None, help="sets VDD (and VREFP=VDD, VCM=VDD/2 unless --set)")
    p.add_argument("--jobs", type=int, default=None)
    p.add_argument("--tag", default="", help="suffix for the results folder")
    p.add_argument("--pvt", action="store_true", help="sweep --corners/--temps/--vdds")
    p.add_argument("--corners", default="tt,ss,ff,sf,fs")
    p.add_argument("--temps", default="-40,27,125")
    p.add_argument("--vdds", default="")
    p.add_argument("--quick", action="store_true", help="fewer points (fast sanity run)")
    return p


def run_one(name, args, extra, cfg_over):
    modname, needs_fsm = BENCHES[name]
    mod = importlib.import_module(modname)
    bp = argparse.ArgumentParser(prog=f"run.py {name}")
    if hasattr(mod, "add_args"):
        mod.add_args(bp)
    bargs, unknown = bp.parse_known_args(extra)
    bargs.quick = args.quick
    cfg = cfgmod.load(args.config, args.set + cfg_over)
    if args.jobs:
        cfg.JOBS = args.jobs
    tag = args.tag
    sub = name + (f"_{tag}" if tag else "")
    out_dir = os.path.join(cfg.RESULTS_DIR, sub)
    print(f"\n=== {name} ===  ({cfgmod.describe(cfg)})")
    lib = load_library(cfg)
    for w in lib.warnings:
        print(f"  warning: {w}")
    rep = Report(name, out_dir, cfg)

    class Ctx:
        pass
    ctx = Ctx()
    ctx.cfg, ctx.lib, ctx.out_dir, ctx.rep, ctx.args = cfg, lib, out_dir, rep, bargs
    t0 = time.time()
    try:
        mod.run(ctx, bargs)
        status = "PASS" if rep.passed else "FAIL"
    except (SimError, NetlistError) as e:
        status = "ERROR"
        print(f"  ERROR: {e}")
        rep.notes.append(f"ERROR: {e}")
    except Exception as e:  # keep going with other benches
        rep.note(f"ERROR: {e!r}")
        status = "ERROR"
        traceback.print_exc()
    rep.save()
    print(rep.table())
    print(f"--> {name}: {status}   ({time.time() - t0:.0f} s)   results: {out_dir}")
    return name, status, rep


def main(argv=None):
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    if args.bench == "list":
        for k, (m, fsm) in BENCHES.items():
            mod = importlib.import_module(m)
            print(f"  {k:<16} {'[needs FSM netlist] ' if fsm else ''}{(mod.__doc__ or '').strip().splitlines()[0]}")
        print("  groups:", ", ".join(f"{g} = {' '.join(v)}" for g, v in GROUPS.items()))
        return 0
    if args.bench == "selftest":
        # checks ngspice/PDK/harness end-to-end with the reference FSM in selftest/ (NOT your design)
        args.set = args.set + ["FSM_NETLIST='{HERE}/selftest/ref_sar_fsm_wrapper.spice'",
                               "RESULTS_DIR='{HERE}/results_selftest'"]
        args.quick = True
        args.bench = "adc"
        names = ["adc_timing", "fsm", "adc_static", "adc_dynamic"]
    else:
        names = GROUPS.get(args.bench, [args.bench])
    for n in names:
        if n not in BENCHES:
            parser.error(f"unknown bench {n!r}; try 'list'")

    base_over = []
    if args.corner:
        base_over.append(f"CORNER='{args.corner}'")
    if args.temp is not None:
        base_over.append(f"TEMP={args.temp}")
    if args.vdd is not None:
        base_over += [f"VDD={args.vdd}", f"VREFP={args.vdd}", f"VCM={args.vdd / 2}"]

    pvt_points = [None]
    if args.pvt:
        vdds = [float(v) for v in args.vdds.split(",") if v] or [None]
        pvt_points = list(itertools.product(args.corners.split(","),
                                            [float(t) for t in args.temps.split(",")], vdds))
    summary = []
    for pt in pvt_points:
        over = list(base_over)
        tag0 = args.tag
        if pt is not None:
            corner, temp, vdd = pt
            over += [f"CORNER='{corner}'", f"TEMP={temp}"]
            if vdd is not None:
                over += [f"VDD={vdd}", f"VREFP={vdd}", f"VCM={vdd / 2}"]
            args.tag = "_".join(x for x in [tag0, corner, f"{temp:g}C"] + ([f"{vdd:g}V"] if vdd else []) if x)
        for n in names:
            summary.append((pt, *run_one(n, args, extra, over)))
        args.tag = tag0

    print("\nsummary")
    for pt, n, st, _ in summary:
        print(f"  {n:<16} {'' if pt is None else pt!s:<24} {st}")
    if args.pvt:
        cfg = cfgmod.load(args.config, args.set)
        path = os.path.join(cfg.RESULTS_DIR, f"pvt_{args.bench}{'_' + args.tag if args.tag else ''}.csv")
        keys = []
        for _, _, _, rep in summary:
            for r in rep.rows:
                if (r["key"]) not in keys:
                    keys.append(r["key"])
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["bench", "corner", "temp", "vdd", "status"] + keys)
            for pt, n, st, rep in summary:
                vals = {r["key"]: r["value"] for r in rep.rows}
                w.writerow([n, pt[0], pt[1], pt[2], st] + [vals.get(k, "") for k in keys])
        print(f"PVT table: {path}")
    return 0 if all(s == "PASS" for _, _, s, _ in summary) else 1


if __name__ == "__main__":
    sys.exit(main())
