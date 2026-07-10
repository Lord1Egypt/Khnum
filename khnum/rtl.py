"""Verilog-2001 RTL emitters for Khnum memory primitives.

Design rules (do not break these — they are what makes Khnum portable):
  * Emit plain Verilog-2001: works in Verilator, Icarus, Yosys, and every
    commercial tool. No SystemVerilog in generated DUT code.
  * One `always` block per memory array (Verilator rejects multi-driven
    memories from separate processes).
  * Read-first semantics everywhere: read-during-write to the same address
    returns the OLD data. This is the safest default and maps to both
    Xilinx/Lattice BRAM and standard-cell RAM.
  * Byte-enable writes use an indexed part-select for-loop, which both
    synthesizes cleanly and infers BRAM byte-write enables.
"""

import json
import math

KINDS = ("sram_1rw", "sram_1r1w", "sram_2r1w", "rf_2r1w_ff", "fifo_sync", "fifo_async")

RF_MAX_DEPTH = 64  # flop-based register files get expensive fast


class Config:
    """Validated configuration for one memory instance."""

    def __init__(self, kind, depth, width, byte_en=False, name=None, ecc=False,
                 bank_depth=1, bank_width=1):
        if kind not in KINDS:
            raise ValueError("unknown kind %r (choose from %s)" % (kind, ", ".join(KINDS)))
        if depth < 2 or depth > (1 << 24):
            raise ValueError("depth must be in [2, 2^24], got %d" % depth)
        if width < 1 or width > 4096:
            raise ValueError("width must be in [1, 4096], got %d" % width)
        if byte_en and width % 8 != 0:
            raise ValueError("--byte-en requires width to be a multiple of 8, got %d" % width)
        if kind == "rf_2r1w_ff" and depth > RF_MAX_DEPTH:
            raise ValueError("rf_2r1w_ff is flop-based; depth capped at %d (use sram_2r1w "
                             "for deeper arrays), got %d" % (RF_MAX_DEPTH, depth))
        if kind.startswith("fifo") and byte_en:
            raise ValueError("--byte-en makes no sense on FIFOs (whole words only)")
        if kind == "fifo_async" and (depth < 4 or depth & (depth - 1)):
            raise ValueError("fifo_async requires power-of-2 depth >= 4 (gray-coded "
                             "pointers), got %d" % depth)
        if ecc and not kind.startswith("sram_"):
            raise ValueError("--ecc is supported on sram kinds only, got %s" % kind)
        if ecc and byte_en:
            raise ValueError("--ecc and --byte-en are mutually exclusive (masked writes "
                             "would need read-modify-write under ECC)")
        if ecc:
            from .ecc import secded_params
            secded_params(width)  # validates width range for ECC
        if bank_depth < 1 or bank_width < 1:
            raise ValueError("bank factors must be >= 1, got depth=%d width=%d"
                             % (bank_depth, bank_width))
        banked = bank_depth > 1 or bank_width > 1
        if banked:
            if not (kind.startswith("sram_") or kind == "rf_2r1w_ff"):
                raise ValueError("banking is supported on sram_* / rf_2r1w_ff only, "
                                 "not %s (FIFO ordering can't be tiled)" % kind)
            if byte_en or ecc:
                raise ValueError("banking excludes --byte-en / --ecc (plain slice/concat "
                                 "data path only)")
            if bank_width > 1 and width % bank_width != 0:
                raise ValueError("--bank-width %d must divide width %d"
                                 % (bank_width, width))
            if bank_depth > 1:
                if depth & (depth - 1):
                    raise ValueError("--bank-depth requires power-of-2 depth, got %d" % depth)
                if bank_depth & (bank_depth - 1):
                    raise ValueError("--bank-depth must be a power of 2, got %d" % bank_depth)
                if depth % bank_depth != 0:
                    raise ValueError("--bank-depth %d must divide depth %d"
                                     % (bank_depth, depth))
                if depth // bank_depth < 2:
                    raise ValueError("per-bank depth must be >= 2 (bank-depth %d too large "
                                     "for depth %d)" % (bank_depth, depth))
        self.kind = kind
        self.depth = depth
        self.width = width
        self.byte_en = byte_en
        self.ecc = ecc
        self.bank_depth = bank_depth
        self.bank_width = bank_width
        self.banked = banked
        bk = "_bk%dx%d" % (bank_depth, bank_width) if banked else ""
        self.name = name or "khnum_%s_%dx%d%s%s%s" % (
            kind, depth, width, "_be" if byte_en else "", "_ecc" if ecc else "", bk)
        self.aw = max(1, math.ceil(math.log2(depth)))
        self.lanes = width // 8 if byte_en else 1

    def manifest(self):
        async_read = self.kind in ("rf_2r1w_ff", "fifo_sync", "fifo_async")
        if self.ecc:
            from .ecc import code_width
            extra = {
                "ecc": {
                    "scheme": "hamming-secded",
                    "data_width": self.width,
                    "code_width": code_width(self.width),
                },
                "children": [self.name + "_core", self.name + "_secded_enc",
                             self.name + "_secded_dec"],
            }
        elif self.banked:
            extra = {
                "banking": {
                    "bank_depth": self.bank_depth,
                    "bank_width": self.bank_width,
                    "num_banks": self.bank_depth * self.bank_width,
                    "bank_depth_words": self.depth // self.bank_depth,
                    "bank_width_bits": self.width // self.bank_width,
                },
                "children": [self.name + "_mac"],
            }
        else:
            extra = {}
        base = self._manifest_base(async_read)
        base.update(extra)
        return base

    def _manifest_base(self, async_read):
        return {
            "generator": "khnum",
            "kind": self.kind,
            "name": self.name,
            "depth": self.depth,
            "width": self.width,
            "byte_en": self.byte_en,
            "addr_width": self.aw,
            "write_lanes": self.lanes,
            "read_latency": 0 if async_read else 1,
            "rdw_behavior": "first-word-fall-through" if self.kind.startswith("fifo")
                            else "read-first (old data)",
            "views": ["rtl", "tb"],
        }

    def manifest_json(self):
        return json.dumps(self.manifest(), indent=2) + "\n"


def _header(cfg, ports_doc):
    return (
        "// -----------------------------------------------------------------------------\n"
        "// %s — generated by Khnum, the ram-headed god of memory\n"
        "// kind=%s depth=%d width=%d byte_en=%s | read latency 1, read-first RDW\n"
        "// https://github.com/Lord1Egypt/Khnum\n"
        "// -----------------------------------------------------------------------------\n"
        "%s" % (cfg.name, cfg.kind, cfg.depth, cfg.width, cfg.byte_en, ports_doc)
    )


def _write_block(cfg, we_expr, addr_sig, data_sig, mask_sig):
    """Write logic; byte-enabled writes use a for-loop of lane part-selects."""
    if cfg.byte_en:
        return (
            "      if (%s) begin\n"
            "        for (lane = 0; lane < %d; lane = lane + 1) begin\n"
            "          if (%s[lane]) mem[%s][lane*8 +: 8] <= %s[lane*8 +: 8];\n"
            "        end\n"
            "      end\n" % (we_expr, cfg.lanes, mask_sig, addr_sig, data_sig)
        )
    return "      if (%s) mem[%s] <= %s;\n" % (we_expr, addr_sig, data_sig)


def emit_rtl(cfg):
    if cfg.kind == "sram_1rw":
        text = _emit_sram_1rw(cfg)
    elif cfg.kind == "sram_1r1w":
        text = _emit_sram_1r1w(cfg)
    elif cfg.kind == "sram_2r1w":
        text = _emit_sram_2r1w(cfg)
    elif cfg.kind == "rf_2r1w_ff":
        return _emit_rf_2r1w_ff(cfg)
    else:
        from .fifo import emit_fifo
        return emit_fifo(cfg)
    # Embed the read-first formal proof (full-word or per-byte-lane) (P2).
    text = _splice_formal(text, _formal_for(cfg))
    return text


def _emit_rf_2r1w_ff(cfg):
    mask_port = "  input  wire [%d:0]  wmask,   // per-byte write lane enable\n" % (cfg.lanes - 1) if cfg.byte_en else ""
    doc = "// Flop-based register file: 1 write port + 2 ASYNC (combinational) read ports.\n"
    lane_decl = "  integer lane;\n" if cfg.byte_en else ""
    body = _write_block(cfg, "we", "waddr", "wdata", "wmask")
    return _header(cfg, doc) + (
        "module %s (\n"
        "  input  wire         clk,\n"
        "  input  wire         we,\n"
        "  input  wire [%d:0]  waddr,\n"
        "  input  wire [%d:0]  wdata,\n"
        "%s"
        "  input  wire [%d:0]  raddr0,\n"
        "  output wire [%d:0]  rdata0,  // asynchronous read, latency 0\n"
        "  input  wire [%d:0]  raddr1,\n"
        "  output wire [%d:0]  rdata1   // asynchronous read, latency 0\n"
        ");\n"
        "  reg [%d:0] mem [0:%d];\n"
        "%s"
        "  always @(posedge clk) begin\n"
        "%s"
        "  end\n"
        "  assign rdata0 = mem[raddr0];\n"
        "  assign rdata1 = mem[raddr1];\n"
        "endmodule\n"
        % (cfg.name, cfg.aw - 1, cfg.width - 1, mask_port, cfg.aw - 1,
           cfg.width - 1, cfg.aw - 1, cfg.width - 1,
           cfg.width - 1, cfg.depth - 1, lane_decl,
           _indent_write(body))
    )


def _emit_sram_1rw(cfg):
    mask_port = "  input  wire [%d:0]  wmask,   // per-byte write lane enable\n" % (cfg.lanes - 1) if cfg.byte_en else ""
    doc = "// Single port: one shared read/write port, synchronous read.\n"
    lane_decl = "  integer lane;\n" if cfg.byte_en else ""
    body = _write_block(cfg, "we", "addr", "wdata", "wmask")
    return _header(cfg, doc) + (
        "module %s (\n"
        "  input  wire         clk,\n"
        "  input  wire         ce,      // chip enable (gates both read and write)\n"
        "  input  wire         we,      // write enable\n"
        "  input  wire [%d:0]  addr,\n"
        "  input  wire [%d:0]  wdata,\n"
        "%s"
        "  output reg  [%d:0]  rdata    // valid 1 cycle after ce, read-first\n"
        ");\n"
        "  reg [%d:0] mem [0:%d];\n"
        "%s"
        "  always @(posedge clk) begin\n"
        "    if (ce) begin\n"
        "%s"
        "      rdata <= mem[addr];\n"
        "    end\n"
        "  end\n"
        "endmodule\n"
        % (cfg.name, cfg.aw - 1, cfg.width - 1, mask_port, cfg.width - 1,
           cfg.width - 1, cfg.depth - 1, lane_decl, body)
    )


def _emit_sram_1r1w(cfg):
    mask_port = "  input  wire [%d:0]  wmask,   // per-byte write lane enable\n" % (cfg.lanes - 1) if cfg.byte_en else ""
    doc = "// Dual port: one write port + one read port, same clock, synchronous read.\n"
    lane_decl = "  integer lane;\n" if cfg.byte_en else ""
    body = _write_block(cfg, "we", "waddr", "wdata", "wmask")
    return _header(cfg, doc) + (
        "module %s (\n"
        "  input  wire         clk,\n"
        "  input  wire         we,\n"
        "  input  wire [%d:0]  waddr,\n"
        "  input  wire [%d:0]  wdata,\n"
        "%s"
        "  input  wire         re,\n"
        "  input  wire [%d:0]  raddr,\n"
        "  output reg  [%d:0]  rdata    // valid 1 cycle after re, read-first\n"
        ");\n"
        "  reg [%d:0] mem [0:%d];\n"
        "%s"
        "  always @(posedge clk) begin\n"
        "%s"
        "    if (re) rdata <= mem[raddr];\n"
        "  end\n"
        "endmodule\n"
        % (cfg.name, cfg.aw - 1, cfg.width - 1, mask_port, cfg.aw - 1,
           cfg.width - 1, cfg.width - 1, cfg.depth - 1, lane_decl,
           _indent_write(body))
    )


def _emit_sram_2r1w(cfg):
    mask_port = "  input  wire [%d:0]  wmask,   // per-byte write lane enable\n" % (cfg.lanes - 1) if cfg.byte_en else ""
    doc = "// Triple port: one write port + two independent read ports, same clock.\n"
    lane_decl = "  integer lane;\n" if cfg.byte_en else ""
    body = _write_block(cfg, "we", "waddr", "wdata", "wmask")
    return _header(cfg, doc) + (
        "module %s (\n"
        "  input  wire         clk,\n"
        "  input  wire         we,\n"
        "  input  wire [%d:0]  waddr,\n"
        "  input  wire [%d:0]  wdata,\n"
        "%s"
        "  input  wire         re0,\n"
        "  input  wire [%d:0]  raddr0,\n"
        "  output reg  [%d:0]  rdata0,  // valid 1 cycle after re0, read-first\n"
        "  input  wire         re1,\n"
        "  input  wire [%d:0]  raddr1,\n"
        "  output reg  [%d:0]  rdata1   // valid 1 cycle after re1, read-first\n"
        ");\n"
        "  reg [%d:0] mem [0:%d];\n"
        "%s"
        "  always @(posedge clk) begin\n"
        "%s"
        "    if (re0) rdata0 <= mem[raddr0];\n"
        "    if (re1) rdata1 <= mem[raddr1];\n"
        "  end\n"
        "endmodule\n"
        % (cfg.name, cfg.aw - 1, cfg.width - 1, mask_port, cfg.aw - 1,
           cfg.width - 1, cfg.aw - 1, cfg.width - 1,
           cfg.width - 1, cfg.depth - 1, lane_decl,
           _indent_write(body))
    )


def _indent_write(block):
    """The 1rw emitter nests writes under `if (ce)`; the others sit one level up."""
    out = []
    for line in block.splitlines(True):
        out.append(line[2:] if line.startswith("      ") else line)
    return "".join(out)


# --- Formal properties (P2) -------------------------------------------------
# Every synchronous SRAM ships an embedded read-first proof, active only under
# `` `ifdef FORMAL `` (invisible to Verilator/Icarus/synthesis, which never
# define it). The property is a symbolic-address scoreboard: pick one arbitrary
# but fixed address `f_addr`, mirror writes to it in a shadow reg, capture the
# PRE-write shadow value on every read of that address (read-first), and assert
# the registered rdata matches one cycle later. `tools/formal.py` discharges it
# with yosys+z3 (async2sync, vacuity-counted) and `tools/mutate.py` proves it is
# non-vacuous. Byte-enable variants use `_formal_sram_be`: the scoreboard tracks
# validity and expected data PER LANE, since a masked write updates only some
# lanes (a naive full-word model provably FAILS on --byte-en).

def _splice_formal(text, fblock):
    i = text.rstrip().rfind("endmodule")
    return text[:i] + fblock + text[i:]


def _formal_sram(cfg, read_ports, wr_cond, wr_addr):
    """read_ports: list of (suffix, read_enable_expr, read_addr_expr)."""
    aw, w = cfg.aw, cfg.width
    L = []
    L.append("`ifdef FORMAL")
    L.append("  // Khnum read-first proof: symbolic-address scoreboard (yosys+z3).")
    L.append("  (* anyconst *) reg [%d:0] f_addr;" % (aw - 1))
    L.append("  reg [%d:0] f_data;" % (w - 1))
    L.append("  reg        f_valid = 1'b0;")
    for suf, _, _ in read_ports:
        L.append("  reg        f_rd%s = 1'b0;" % suf)
        L.append("  reg [%d:0] f_exp%s;" % (w - 1, suf))
        L.append("  reg        f_ev%s = 1'b0;" % suf)
    L.append("  always @(posedge clk) begin")
    for suf, re_expr, raddr in read_ports:
        L.append("    if ((%s) && %s == f_addr) begin" % (re_expr, raddr))
        L.append("      f_rd%s <= 1'b1; f_exp%s <= f_data; f_ev%s <= f_valid;" % (suf, suf, suf))
        L.append("    end else f_rd%s <= 1'b0;" % suf)
    L.append("    if ((%s) && %s == f_addr) begin" % (wr_cond, wr_addr))
    L.append("      f_data <= wdata; f_valid <= 1'b1;")
    L.append("    end")
    L.append("  end")
    L.append("  always @(posedge clk) begin")
    for suf, _, _ in read_ports:
        L.append("    if (f_rd%s && f_ev%s) assert (rdata%s == f_exp%s);" % (suf, suf, suf, suf))
    L.append("  end")
    L.append("`endif")
    return "\n".join(L) + "\n"


def _formal_sram_be(cfg, read_ports, wr_cond, wr_addr):
    """Per-byte-lane read-first scoreboard. A masked write updates only the
    lanes whose wmask bit is set, so validity and expected data are tracked per
    lane; the full-word `_formal_sram` model provably fails on --byte-en."""
    aw, w, lanes = cfg.aw, cfg.width, cfg.lanes
    L = []
    L.append("`ifdef FORMAL")
    L.append("  // Khnum read-first byte-lane proof: per-lane symbolic-address scoreboard.")
    L.append("  (* anyconst *) reg [%d:0] f_addr;" % (aw - 1))
    L.append("  reg [%d:0] f_data;" % (w - 1))
    L.append("  reg [%d:0] f_valid = %d'b0;" % (lanes - 1, lanes))
    for suf, _, _ in read_ports:
        L.append("  reg        f_rd%s = 1'b0;" % suf)
        L.append("  reg [%d:0] f_exp%s;" % (w - 1, suf))
        L.append("  reg [%d:0] f_ev%s = %d'b0;" % (lanes - 1, suf, lanes))
    L.append("  integer fl;")
    L.append("  always @(posedge clk) begin")
    for suf, re_expr, raddr in read_ports:
        L.append("    if ((%s) && %s == f_addr) begin" % (re_expr, raddr))
        L.append("      f_rd%s <= 1'b1; f_exp%s <= f_data; f_ev%s <= f_valid;" % (suf, suf, suf))
        L.append("    end else f_rd%s <= 1'b0;" % suf)
    L.append("    if ((%s) && %s == f_addr) begin" % (wr_cond, wr_addr))
    L.append("      for (fl = 0; fl < %d; fl = fl + 1) begin" % lanes)
    L.append("        if (wmask[fl]) begin")
    L.append("          f_data[fl*8 +: 8] <= wdata[fl*8 +: 8];")
    L.append("          f_valid[fl] <= 1'b1;")
    L.append("        end")
    L.append("      end")
    L.append("    end")
    L.append("  end")
    L.append("  always @(posedge clk) begin")
    L.append("    for (fl = 0; fl < %d; fl = fl + 1) begin" % lanes)
    for suf, _, _ in read_ports:
        L.append("      if (f_rd%s && f_ev%s[fl]) "
                 "assert (rdata%s[fl*8 +: 8] == f_exp%s[fl*8 +: 8]);" % (suf, suf, suf, suf))
    L.append("    end")
    L.append("  end")
    L.append("`endif")
    return "\n".join(L) + "\n"


def _formal_for(cfg):
    builder = _formal_sram_be if cfg.byte_en else _formal_sram
    if cfg.kind == "sram_1rw":
        return builder(cfg, [("", "ce", "addr")], "ce && we", "addr")
    if cfg.kind == "sram_1r1w":
        return builder(cfg, [("", "re", "raddr")], "we", "waddr")
    if cfg.kind == "sram_2r1w":
        return builder(cfg, [("0", "re0", "raddr0"), ("1", "re1", "raddr1")],
                       "we", "waddr")
    return ""
