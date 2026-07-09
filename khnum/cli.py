"""Khnum command-line interface.

Non-blocking by design: every action is driven by flags, never input().
    python3 -m khnum gen --kind sram_1rw --depth 1024 --width 32 --byte-en -o build
    python3 -m khnum list
"""

import argparse
import os
import sys

from . import __version__
from .rtl import KINDS, Config, emit_rtl
from .tb import emit_tb


def _cmd_gen(args):
    cfg = Config(args.kind, args.depth, args.width, byte_en=args.byte_en, name=args.name)
    outdir = args.output
    os.makedirs(outdir, exist_ok=True)
    products = {
        os.path.join(outdir, cfg.name + ".v"): emit_rtl(cfg),
        os.path.join(outdir, cfg.name + ".manifest.json"): cfg.manifest_json(),
    }
    if not args.no_tb:
        products[os.path.join(outdir, cfg.name + "_tb.v")] = emit_tb(cfg)
    for path, text in sorted(products.items()):
        with open(path, "w") as fh:
            fh.write(text)
        print("khnum: wrote %s" % path)
    bits = cfg.depth * cfg.width
    print("khnum: %s ready — %d words x %d bits = %d Kib, addr %d bits, RDW read-first"
          % (cfg.name, cfg.depth, cfg.width, bits // 1024 if bits >= 1024 else bits, cfg.aw))
    return 0


def _cmd_list(_args):
    print("Khnum v%s — available memory kinds:" % __version__)
    descriptions = {
        "sram_1rw": "single-port SRAM: one shared read/write port, sync read",
        "sram_1r1w": "simple dual-port SRAM: 1 write + 1 read port, sync read",
        "sram_2r1w": "register-file-style SRAM: 1 write + 2 read ports, sync read",
        "rf_2r1w_ff": "flop register file: 1 write + 2 ASYNC read ports (depth <= 64)",
        "fifo_sync": "single-clock FIFO: FWFT, full/empty/level flags",
        "fifo_async": "dual-clock CDC FIFO: gray pointers + 2-FF sync (pow2 depth >= 4)",
    }
    for kind in KINDS:
        print("  %-10s  %s" % (kind, descriptions[kind]))
    print("options: --depth N --width N [--byte-en] [--name STR] [-o DIR] [--no-tb]")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="khnum",
        description="Khnum — the ram-headed god of memory. "
                    "Zero-dependency memory compiler: verified RTL + testbenches.",
    )
    p.add_argument("--version", action="version", version="khnum " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("gen", help="generate one memory instance (RTL + TB + manifest)")
    g.add_argument("--kind", required=True, choices=KINDS)
    g.add_argument("--depth", required=True, type=int, help="number of words (2..2^24)")
    g.add_argument("--width", required=True, type=int, help="bits per word (1..4096)")
    g.add_argument("--byte-en", action="store_true", help="per-byte write lanes (width %% 8 == 0)")
    g.add_argument("--name", default=None, help="override module name")
    g.add_argument("-o", "--output", default="build", help="output directory (default: build)")
    g.add_argument("--no-tb", action="store_true", help="skip testbench emission")
    g.set_defaults(func=_cmd_gen)

    l = sub.add_parser("list", help="list available memory kinds")
    l.set_defaults(func=_cmd_list)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print("khnum: error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
