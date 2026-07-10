# Integrating Khnum memories into a SoC

Khnum generates one memory instance at a time as plain Verilog-2001 + a
manifest. This doc covers how those drop into a real design.

## 1. Pick the kind for the job

| Need | Khnum kind |
|---|---|
| Instruction/data scratchpad, cache way, tightly-coupled memory | `sram_1rw` (shared R/W port) or `sram_1r1w` (separate ports, same clock) |
| CPU register file / multi-read datapath state | `sram_2r1w` (synchronous read, deeper/wider) or `rf_2r1w_ff` (asynchronous read, depth ≤ 64) |
| Producer/consumer queue, single clock domain | `fifo_sync` |
| Clock-domain-crossing queue | `fifo_async` (gray-coded pointers, 2-FF synchronizers) |
| Safety/reliability-critical storage | any `sram_*` with `--ecc` (Hamming SECDED) |
| Bigger than one macro should reasonably be | any bankable kind with `--bank-depth`/`--bank-width` |

## 2. Generate, verify standalone, then integrate

```bash
python3 -m khnum gen --kind sram_1rw --depth 1024 --width 32 --byte-en -o rtl/mem
```

This writes the DUT (`.v`), a self-checking testbench (`_tb.v`), and a
manifest (`.manifest.json`, — depth/width/`addr_width`/`read_latency`/
`rdw_behavior`/etc., for your build scripts to consume programmatically
instead of re-deriving these from the RTL). **Run the testbench standalone
before wiring the module into your design** — same command
`tools/test_all.py` uses per config (see its `_lint_and_sim` for the exact
Verilator invocation). A memory that hasn't passed its own TB has no business
being integrated into a bigger design where failures are harder to isolate.

Then drop the `.v` file into your RTL tree and instantiate it like any other
module — the ports are exactly what the manifest and the kind's doc comment
in `khnum/rtl.py` describe (`read_latency: 1` for the sync kinds means
registered read data one cycle after `re`/`ce`; `0` for `rf_2r1w_ff` and both
FIFOs means combinational/FWFT).

## 3. Worked example: a CPU register file

[KemetCore](https://github.com/Lord1Egypt/KemetCore)'s SethCore has a real
RV32 register file, `seth_regfile.sv` — 32 x 32-bit, one synchronous write
port, two asynchronous read ports. That's exactly `rf_2r1w_ff`'s port shape
(`--kind rf_2r1w_ff --depth 32 --width 32`).

It is **not a drop-in swap without a thin wrapper**, and that's worth being
explicit about rather than overclaiming compatibility: SethCore's regfile
synchronously resets all 32 registers to 0 and hardwires `x0` to always read
as zero — both are ISA-specific business logic, not general memory-array
behavior, so Khnum's generator deliberately doesn't bake them in (a memory
generator that started encoding "this address always reads zero" would stop
being a general-purpose memory generator). The integration pattern is: put
that logic in a caller-side wrapper module around the Khnum-generated
`rf_2r1w_ff` array (mux `x0` reads to zero, gate `we` for x0 writes off, add
reset if your integration needs one) rather than asking Khnum to special-case
it. This is the same boundary every memory compiler draws — OpenRAM/DFFRAM
generate the array, the SoC's glue logic still owns architectural semantics.

## 4. FPGA and ASIC targets

- **FPGA**: `sram_1rw`/`sram_1r1w`/`sram_2r1w` are proven (see `docs/FPGA.md`)
  to infer real BRAM (`RAMB18E1`/`RAMB36E1` on Xilinx 7-series,
  `SB_RAM40_4K` on iCE40) via plain `synth_xilinx`/`synth_ice40` — no special
  synthesis attributes or vendor macro instantiation needed, so a
  Khnum-generated SRAM in your top-level design should infer BRAM the same
  way, without further coaxing.
- **ASIC**: `harden/designs/sky130hd/<name>/{config.mk,constraint.sdc}` are
  working OpenROAD/ORFS recipes for standard-cell (DFFRAM-style) hardening —
  see `harden/HARDEN_RESULTS.md` for what's actually been proven, and copy the
  closest-sized existing recipe as your starting `config.mk` (watch
  `SYNTH_MEMORY_MAX_BITS`, `CORE_UTILIZATION`/`PLACE_DENSITY` per the notes
  there — a recipe that closes at one size isn't guaranteed to route or close
  timing at 4x the size without retuning).
