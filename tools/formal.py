#!/usr/bin/env python3
"""Khnum formal verification — proves each kind's safety property, non-vacuously.

SRAM configs prove read-first; fifo_sync proves occupancy never over/underflows;
fifo_async proves both gray pointers stay valid gray encodings of their binary
counters (the property the CDC synchronizers depend on). For each config we:
  1. emit the RTL (the property's scoreboard/assertions are embedded under
     `ifdef FORMAL`),
  2. run yosys: read_verilog -formal -DFORMAL -> prep -> async2sync -> write_smt2
     (async2sync is MANDATORY: without it yosys silently drops the $check cells
     and the SMT2 carries ZERO assertions — a vacuous "proof". KemetCore lesson.),
  3. count `yosys-smt2-assert` in the SMT2: 0 => vacuous => FAIL,
  4. bounded model-check with z3 (smtbmc): must be PASSED,
  5. apply the kind's property-breaking mutation and re-check: must be FAILED.

yosys (yowasp) runs in a WASI sandbox that only sees its working directory, so
every invocation uses cwd=<outdir> and bare filenames.

Deps: yowasp-yosys, yowasp-yosys-smtbmc, z3 (dev/CI only, never imported by the
generator). If yosys is missing this prints SKIP and exits 0 so it never blocks
a machine without the formal toolchain — CI installs it and enforces the gate.

Run:  python3 tools/formal.py            # full proof set
      python3 tools/formal.py --depth 12 # override BMC depth
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BUILD = os.path.join(ROOT, "build", "formal")

from khnum.rtl import Config, emit_rtl  # noqa: E402
from tools.mutate import mutate  # noqa: E402

# Small configs keep z3 fast while still exercising the address decode / ports.
# byte-en configs carry per-lane part-selects that z3 solves far slower with
# unroll depth, so they run at a shorter (still sufficient: read-first shows in
# <=2 cycles) bounded depth via the per-entry "bmc" key.
FORMAL_MATRIX = [
    dict(kind="sram_1rw",  depth=8,  width=8),
    dict(kind="sram_1rw",  depth=16, width=16),
    dict(kind="sram_1r1w", depth=8,  width=8),
    dict(kind="sram_2r1w", depth=8,  width=8),
    dict(kind="sram_1rw",  depth=8,  width=16, byte_en=True, bmc=6),
    dict(kind="sram_1r1w", depth=8,  width=16, byte_en=True, bmc=6),
    dict(kind="sram_2r1w", depth=8,  width=16, byte_en=True, bmc=6),
    dict(kind="fifo_sync",  depth=8, width=8),
    dict(kind="fifo_async", depth=8, width=8),
]

FAILURES = []


def _yosys():
    return shutil.which("yowasp-yosys")


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=600)
    return p.returncode, p.stdout


def check(label, ok, detail=""):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILURES.append(label)
        if detail:
            print("       " + "\n       ".join(detail.strip().splitlines()[-12:]))


def _write_smt2(outdir, vfile, top, smt2):
    """Emit SMT2 with async2sync; return (rc, out, assert_count)."""
    script = ("read_verilog -formal -DFORMAL %s; prep -top %s; async2sync; "
              "write_smt2 -wires %s" % (vfile, top, smt2))
    rc, out = run(["yowasp-yosys", "-q", "-p", script], cwd=outdir)
    n = 0
    path = os.path.join(outdir, smt2)
    if os.path.exists(path):
        with open(path) as fh:
            n = fh.read().count("yosys-smt2-assert")
    return rc, out, n


def _bmc(outdir, smt2, depth):
    rc, out = run(["yowasp-yosys-smtbmc", "-s", "z3", "-t", str(depth), smt2], cwd=outdir)
    passed = "Status: PASSED" in out
    failed = "Status: FAILED" in out or "BMC failed" in out
    return passed, failed, out


def prove(entry, default_depth):
    kind, depth, width = entry["kind"], entry["depth"], entry["width"]
    byte_en = entry.get("byte_en", False)
    bmc_depth = entry.get("bmc", default_depth)
    tag = "%s_%dx%d%s" % (kind, depth, width, "_be" if byte_en else "")
    print("[formal] " + tag)
    outdir = os.path.join(BUILD, tag)
    os.makedirs(outdir, exist_ok=True)
    kwargs = {"byte_en": byte_en} if not kind.startswith("fifo") else {}
    cfg = Config(kind, depth, width, **kwargs)
    rtl = emit_rtl(cfg)
    with open(os.path.join(outdir, cfg.name + ".v"), "w") as fh:
        fh.write(rtl)

    rc, out, n = _write_smt2(outdir, cfg.name + ".v", cfg.name, cfg.name + ".smt2")
    check(tag + ": yosys write_smt2", rc == 0, out)
    check(tag + ": non-vacuous (>=1 assertion in SMT2)", n >= 1,
          "assertion count = %d" % n)
    if rc == 0 and n >= 1:
        passed, failed, out = _bmc(outdir, cfg.name + ".smt2", bmc_depth)
        check(tag + ": proof PASSED (bmc %d)" % bmc_depth,
              passed and not failed, out)

    # Mutation: break the kind's property -> the proof MUST now fail.
    mut_kwargs = {"ptr_msb": cfg.aw} if kind == "fifo_async" else {}
    mut = mutate(rtl, kind, **mut_kwargs)
    with open(os.path.join(outdir, cfg.name + "_mut.v"), "w") as fh:
        fh.write(mut)
    rc, out, n = _write_smt2(outdir, cfg.name + "_mut.v", cfg.name, cfg.name + "_mut.smt2")
    if rc == 0 and n >= 1:
        passed, failed, out = _bmc(outdir, cfg.name + "_mut.smt2", bmc_depth)
        check(tag + ": mutant CAUGHT (proof fails on broken RTL)", failed and not passed, out)
    else:
        check(tag + ": mutant SMT2 built", False, out)


def main():
    ap = argparse.ArgumentParser(description="Khnum formal proof runner")
    ap.add_argument("--depth", type=int, default=15, help="BMC unroll depth")
    args = ap.parse_args()

    if _yosys() is None:
        print("formal: yowasp-yosys not found — SKIP (install yowasp-yosys to enforce)")
        return 0
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    for entry in FORMAL_MATRIX:
        prove(entry, args.depth)

    print()
    if FAILURES:
        print("KHNUM FORMAL: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("KHNUM FORMAL: ALL PROVEN (%d configs, non-vacuous + mutation-caught)"
          % len(FORMAL_MATRIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
