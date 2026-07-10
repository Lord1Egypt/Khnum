#!/usr/bin/env python3
"""Khnum FPGA gate — proves generated SRAM maps to real BRAM/SPRAM primitives.

For each SRAM config (depth >= 256, the point at which no sane FPGA vendor
tool falls back to flip-flop arrays) we run yowasp-yosys's `synth_xilinx` and
`synth_ice40` and require the design to end up with true block-RAM cells
(RAMB18E1/RAMB36E1, SB_RAM40_4K) rather than a flip-flop-array fallback.

`-run begin:map_ffram` stops the synth_* flow right after the memory-mapping
stage (`memory_libmap` + the BRAM/LUTRAM techmap), before it reaches the LUT/
ABC mapping stage for the surrounding glue logic. That later stage is where
this machine's yowasp-yosys (a WASM build of yosys) silently truncates output
mid-pass with no error — an environment quirk, not an RTL bug. Since BRAM
cells are fixed primitives ABC never touches, stopping early doesn't change
whether the memory itself got inferred; `stat` right after `map_ffram` is a
faithful readout of BRAM/SPRAM presence.

Deps: yowasp-yosys (dev/CI only, never imported by the generator). If it's
missing this prints SKIP and exits 0, same policy as tools/formal.py.

Run:  python3 tools/test_fpga.py
"""

import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BUILD = os.path.join(ROOT, "build", "fpga")

from khnum.rtl import Config, emit_rtl  # noqa: E402

# depth 256 is comfortably above every vendor's BRAM-vs-LUTRAM threshold;
# covers all 3 SRAM kinds x byte-en on/off.
FPGA_MATRIX = [
    dict(kind="sram_1rw",  depth=256, width=32),
    dict(kind="sram_1rw",  depth=256, width=32, byte_en=True),
    dict(kind="sram_1r1w", depth=256, width=32),
    dict(kind="sram_1r1w", depth=256, width=32, byte_en=True),
    dict(kind="sram_2r1w", depth=256, width=32),
    dict(kind="sram_2r1w", depth=256, width=32, byte_en=True),
]

XILINX_CELL_RE = re.compile(r"^\s*\d+\s+(RAMB18E1|RAMB36E1)\s*$", re.M)
ICE40_CELL_RE = re.compile(r"^\s*\d+\s+(SB_RAM40_4K|SB_SPRAM256KA)\s*$", re.M)

FAILURES = []


def _yosys():
    return shutil.which("yowasp-yosys")


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=300)
    return p.returncode, p.stdout


def check(label, ok, detail=""):
    print("  %s %s" % ("PASS" if ok else "FAIL", label))
    if not ok:
        FAILURES.append(label)
        if detail:
            print("       " + "\n       ".join(detail.strip().splitlines()[-15:]))


def _synth(outdir, vfile, top, family_cmd):
    script = "read_verilog %s; %s -top %s -run begin:map_ffram; stat" % (
        vfile, family_cmd, top)
    return run(["yowasp-yosys", "-p", script], cwd=outdir)


def gate(entry):
    kind, depth, width = entry["kind"], entry["depth"], entry["width"]
    byte_en = entry.get("byte_en", False)
    tag = "%s_%dx%d%s" % (kind, depth, width, "_be" if byte_en else "")
    print("[fpga] " + tag)
    outdir = os.path.join(BUILD, tag)
    os.makedirs(outdir, exist_ok=True)
    cfg = Config(kind, depth, width, byte_en=byte_en)
    rtl = emit_rtl(cfg)
    vfile = cfg.name + ".v"
    with open(os.path.join(outdir, vfile), "w") as fh:
        fh.write(rtl)

    rc, out = _synth(outdir, vfile, cfg.name, "synth_xilinx")
    check(tag + ": synth_xilinx BRAM inference (RAMB18E1/RAMB36E1)",
          rc == 0 and XILINX_CELL_RE.search(out) is not None, out)

    rc, out = _synth(outdir, vfile, cfg.name, "synth_ice40")
    check(tag + ": synth_ice40 BRAM inference (SB_RAM40_4K/SB_SPRAM256KA)",
          rc == 0 and ICE40_CELL_RE.search(out) is not None, out)


def main():
    if _yosys() is None:
        print("fpga: yowasp-yosys not found — SKIP (install yowasp-yosys to enforce)")
        return 0
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(BUILD)

    for entry in FPGA_MATRIX:
        gate(entry)

    print()
    if FAILURES:
        print("KHNUM FPGA GATE: %d FAILURE(S)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("KHNUM FPGA GATE: ALL BRAM/SPRAM INFERRED (%d configs)" % len(FPGA_MATRIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
