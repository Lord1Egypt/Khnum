#!/usr/bin/env python3
"""Khnum full verification harness — exit 0 means everything passed.

Per-config pipeline:
  1. generate RTL + TB + manifest via the CLI (subprocess, like a real user),
  2. Verilator lint (--lint-only -Wall) on the DUT hierarchy alone,
  3. Verilator --binary --timing build of DUTs+TB, run, require KHNUM_TB_PASS.
ECC configs and the standalone SECDED pair emit a multi-file hierarchy, so the
lint/sim step globs every *.v in the output dir (DUTs = non-_tb, TB = _tb).
Also checks CLI hygiene: list/version work, invalid configs exit non-zero,
and nothing ever blocks on stdin.

Stdlib only. Run:  python3 tools/test_all.py
"""

import glob
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build", "test_all")
PY = sys.executable or "python3"

# kind, depth, width, byte_en, ecc — covers non-power-of-2 depths, wide words,
# multi-chunk random data (>32b), byte lanes on every kind, and transparent
# SECDED protection on all three sram kinds.
MATRIX = [
    ("sram_1rw", 64, 32, True, False),
    ("sram_1rw", 100, 8, False, False),
    ("sram_1rw", 512, 72, False, False),
    ("sram_1r1w", 256, 32, False, False),
    ("sram_1r1w", 64, 64, True, False),
    ("sram_2r1w", 32, 32, False, False),
    ("sram_2r1w", 64, 24, True, False),
    ("rf_2r1w_ff", 32, 32, False, False),
    ("rf_2r1w_ff", 64, 24, True, False),
    ("fifo_sync", 16, 8, False, False),
    ("fifo_sync", 100, 16, False, False),
    ("fifo_async", 8, 8, False, False),
    ("fifo_async", 64, 32, False, False),
    ("sram_1rw", 128, 32, False, True),
    ("sram_1r1w", 64, 16, False, True),
    ("sram_2r1w", 32, 64, False, True),
]

# Standalone SECDED encoder/decoder widths (via `khnum ecc`).
ECC_WIDTHS = [8, 32, 64]

# kind, depth, width, bank_depth, bank_width — the banking composer tiles one
# base macro into a larger array; wrapper keeps identical ports so the standard
# TB drives it. Covers deep (address-decode), wide (lane-concat), and grid tiling
# across every bankable kind, incl. the async register file.
BANK_MATRIX = [
    ("sram_1rw", 256, 32, 4, 1),
    ("sram_1rw", 64, 32, 1, 4),
    ("sram_1rw", 512, 64, 8, 2),
    ("sram_1r1w", 256, 32, 4, 2),
    ("sram_2r1w", 128, 16, 2, 1),
    ("sram_2r1w", 64, 32, 2, 2),
    ("rf_2r1w_ff", 32, 32, 2, 1),
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


def _duts_and_tbs(outdir):
    """Split every *.v in outdir into DUTs (non-_tb) and testbenches (_tb.v)."""
    all_v = sorted(glob.glob(os.path.join(outdir, "*.v")))
    duts = [f for f in all_v if not f.endswith("_tb.v")]
    tbs = [f for f in all_v if f.endswith("_tb.v")]
    return duts, tbs


def _lint_and_sim(tag, outdir, name, lint_top=True):
    """Lint the DUT hierarchy -Wall clean, then build+run the TB (top=name_tb).

    lint_top=False skips the hierarchy lint (used when there is no single top
    DUT module, e.g. the standalone enc/dec pair, which are linted separately).
    """
    duts, tbs = _duts_and_tbs(outdir)
    check(tag + ": DUT files present", bool(duts) and bool(tbs),
          "found %r" % (duts + tbs))
    if not duts or not tbs:
        return

    if lint_top:
        ok, _, out = run(["verilator", "--lint-only", "-Wall", "--top", name] + duts,
                         cwd=outdir)
        check(tag + ": lint -Wall clean", ok and "Warning" not in out, out)

    ok, _, out = run(
        ["verilator", "--binary", "--timing", "-j", "2", "-Wno-fatal",
         "--top", name + "_tb"] + duts + tbs + ["-o", "sim"], cwd=outdir)
    check(tag + ": verilate+build TB", ok, out)
    if not ok:
        return

    ok, _, out = run([os.path.join(outdir, "obj_dir", "sim")], cwd=outdir)
    check(tag + ": simulation KHNUM_TB_PASS",
          ok and "KHNUM_TB_PASS" in out and "KHNUM_TB_FAIL" not in out, out)


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
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "rf_2r1w_ff", "--depth", "128",
         "--width", "32", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject rf depth>64 (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "fifo_async", "--depth", "24",
         "--width", "8", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject non-pow2 async fifo depth (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "fifo_sync", "--depth", "16",
         "--width", "16", "--byte-en", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject byte-en on fifo (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "64",
         "--width", "32", "--ecc", "--byte-en", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject --ecc with --byte-en (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "fifo_sync", "--depth", "16",
         "--width", "32", "--ecc", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject --ecc on fifo (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "fifo_sync", "--depth", "16",
         "--width", "32", "--bank-depth", "2", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject banking on fifo (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "100",
         "--width", "32", "--bank-depth", "4", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject --bank-depth on non-pow2 depth (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "64",
         "--width", "30", "--bank-width", "4", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject --bank-width not dividing width (exit 2)", ok, out)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", "sram_1rw", "--depth", "64",
         "--width", "32", "--bank-depth", "2", "--ecc", "-o", os.path.join(BUILD, "bad")],
        cwd=ROOT, expect_rc=2)
    check("reject banking with --ecc (exit 2)", ok, out)


def test_config(kind, depth, width, byte_en, ecc):
    tag = "%s_%dx%d%s%s" % (kind, depth, width,
                            "_be" if byte_en else "", "_ecc" if ecc else "")
    print("[gen] " + tag)
    outdir = os.path.join(BUILD, tag)
    cmd = [PY, "-m", "khnum", "gen", "--kind", kind, "--depth", str(depth),
           "--width", str(width), "-o", outdir]
    if byte_en:
        cmd.append("--byte-en")
    if ecc:
        cmd.append("--ecc")
    ok, _, out = run(cmd, cwd=ROOT)
    check(tag + ": generate", ok, out)
    if not ok:
        return

    name = "khnum_%s" % tag
    man = os.path.join(outdir, name + ".manifest.json")
    with open(man) as fh:
        m = json.load(fh)
    base_ok = m["depth"] == depth and m["width"] == width and m["kind"] == kind
    if ecc:
        ecc_ok = (m.get("ecc", {}).get("scheme") == "hamming-secded"
                  and m["ecc"]["data_width"] == width
                  and "children" in m and len(m["children"]) == 3)
        check(tag + ": manifest sane (ecc)", base_ok and ecc_ok, json.dumps(m))
    else:
        check(tag + ": manifest sane", base_ok, json.dumps(m))

    _lint_and_sim(tag, outdir, name)


def test_bank(kind, depth, width, bank_depth, bank_width):
    tag = "%s_%dx%d_bk%dx%d" % (kind, depth, width, bank_depth, bank_width)
    print("[bank] " + tag)
    outdir = os.path.join(BUILD, tag)
    ok, _, out = run(
        [PY, "-m", "khnum", "gen", "--kind", kind, "--depth", str(depth),
         "--width", str(width), "--bank-depth", str(bank_depth),
         "--bank-width", str(bank_width), "-o", outdir], cwd=ROOT)
    check(tag + ": generate", ok, out)
    if not ok:
        return

    name = "khnum_%s" % tag
    man = os.path.join(outdir, name + ".manifest.json")
    with open(man) as fh:
        m = json.load(fh)
    bk = m.get("banking", {})
    check(tag + ": manifest sane",
          m["depth"] == depth and m["width"] == width and m["kind"] == kind
          and bk.get("bank_depth") == bank_depth
          and bk.get("bank_width") == bank_width
          and bk.get("num_banks") == bank_depth * bank_width
          and m.get("children") == [name + "_mac"], json.dumps(m))

    _lint_and_sim(tag, outdir, name)


def test_ecc_standalone(width):
    tag = "ecc_w%d" % width
    print("[ecc] " + tag)
    outdir = os.path.join(BUILD, tag)
    name = "khnum_secded_w%d" % width
    ok, _, out = run(
        [PY, "-m", "khnum", "ecc", "--width", str(width), "-o", outdir], cwd=ROOT)
    check(tag + ": generate", ok, out)
    if not ok:
        return

    man = os.path.join(outdir, name + ".manifest.json")
    with open(man) as fh:
        m = json.load(fh)
    check(tag + ": manifest sane",
          m["kind"] == "ecc_secded" and m["data_width"] == width, json.dumps(m))

    # lint each module standalone (enc/dec are self-contained, no submodules)
    for mod in ("_enc", "_dec"):
        dut = os.path.join(outdir, name + mod + ".v")
        ok, _, out = run(
            ["verilator", "--lint-only", "-Wall", "--top", name + mod, dut],
            cwd=outdir)
        check(tag + mod + ": lint -Wall clean", ok and "Warning" not in out, out)

    # fault-injection sim: all 1-bit flips corrected, all 2-bit pairs detected
    _lint_and_sim(tag, outdir, name, lint_top=False)


def main():
    if shutil.which("verilator") is None:
        print("ERROR: verilator not found on PATH — install it first")
        return 1
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    test_cli_hygiene()
    for kind, depth, width, byte_en, ecc in MATRIX:
        test_config(kind, depth, width, byte_en, ecc)
    for kind, depth, width, bd, bw in BANK_MATRIX:
        test_bank(kind, depth, width, bd, bw)
    for width in ECC_WIDTHS:
        test_ecc_standalone(width)

    print()
    if FAILURES:
        print("KHNUM TEST_ALL: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("KHNUM TEST_ALL: ALL GREEN (%d configs + %d banked + %d ECC pairs + CLI hygiene)"
          % (len(MATRIX), len(BANK_MATRIX), len(ECC_WIDTHS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
