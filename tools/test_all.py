#!/usr/bin/env python3
"""Khnum full verification harness — exit 0 means everything passed.

Per-config pipeline:
  1. generate RTL + TB + manifest via the CLI (subprocess, like a real user),
  2. Verilator lint (--lint-only -Wall) on the DUT alone,
  3. Verilator --binary --timing build of DUT+TB, run, require KHNUM_TB_PASS.
Also checks CLI hygiene: list/version work, invalid configs exit non-zero,
and nothing ever blocks on stdin.

Stdlib only. Run:  python3 tools/test_all.py
"""

import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "test_all")
PY = sys.executable or "python3"

# kind, depth, width, byte_en — covers non-power-of-2 depths, wide words,
# multi-chunk random data (>32b), and byte lanes on every kind.
MATRIX = [
    ("sram_1rw", 64, 32, True),
    ("sram_1rw", 100, 8, False),
    ("sram_1rw", 512, 72, False),
    ("sram_1r1w", 256, 32, False),
    ("sram_1r1w", 64, 64, True),
    ("sram_2r1w", 32, 32, False),
    ("sram_2r1w", 64, 24, True),
]

FAILURES = []


def run(cmd, cwd=None, expect_rc=0):
    proc = subprocess.run(
        cmd, cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=600,
    )
    ok = proc.returncode == expect_rc
    return ok, proc.returncode, proc.stdout


def check(label, ok, detail=""):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILURES.append(label)
        if detail:
            print("       " + "\n       ".join(detail.strip().splitlines()[-15:]))


def test_cli_hygiene():
    print("[cli] hygiene checks")
    ok, _, out = run([PY, "-m", "khnum", "list"], cwd=ROOT)
    check("khnum list", ok and "sram_1rw" in out, out)
    ok, _, out = run([PY, "-m", "khnum", "--version"], cwd=ROOT)
    check("khnum --version", ok and "khnum" in out, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "64",
         "--width", "33", "--byte-en", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject byte-en with width%8!=0 (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "1",
         "--width", "8", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject depth<2 (exit 2)", ok, out)


def test_config(kind, depth, width, byte_en):
    tag = "%s_%dx%d%s" % (kind, depth, width, "_be" if byte_en else "")
    print("[gen] " + tag)
    outdir = os.path.join(BUILD, tag)
    cmd = [PY, "-m", "khnum", "gen", "--kind", kind, "--depth", str(depth),
           "--width", str(width), "-o", outdir]
    if byte_en:
        cmd.append("--byte-en")
    ok, _, out = run(cmd, cwd=ROOT)
    check(tag + ": generate", ok, out)
    if not ok:
        return

    name = "khnum_%s" % tag
    dut = os.path.join(outdir, name + ".v")
    tb = os.path.join(outdir, name + "_tb.v")
    man = os.path.join(outdir, name + ".manifest.json")

    with open(man) as fh:
        m = json.load(fh)
    check(tag + ": manifest sane",
          m["depth"] == depth and m["width"] == width and m["kind"] == kind,
          json.dumps(m))

    ok, _, out = run(["verilator", "--lint-only", "-Wall", dut], cwd=outdir)
    check(tag + ": lint -Wall clean", ok and "Warning" not in out, out)

    ok, _, out = run(
        ["verilator", "--binary", "--timing", "-j", "2", "-Wno-fatal",
         "--top", name + "_tb", dut, tb, "-o", "sim"], cwd=outdir)
    check(tag + ": verilate+build TB", ok, out)
    if not ok:
        return

    ok, _, out = run([os.path.join(outdir, "obj_dir", "sim")], cwd=outdir)
    check(tag + ": simulation KHNUM_TB_PASS",
          ok and "KHNUM_TB_PASS" in out and "KHNUM_TB_FAIL" not in out, out)


def main():
    if shutil.which("verilator") is None:
        print("ERROR: verilator not found on PATH — install it first")
        return 1
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    test_cli_hygiene()
    for kind, depth, width, byte_en in MATRIX:
        test_config(kind, depth, width, byte_en)

    print()
    if FAILURES:
        print("KHNUM TEST_ALL: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("KHNUM TEST_ALL: ALL GREEN (%d configs + CLI hygiene)" % len(MATRIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
