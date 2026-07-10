# FPGA inference results (P3 — The FPGA Gate)

Every Khnum SRAM kind (`sram_1rw`, `sram_1r1w`, `sram_2r1w`) is mechanically proven to
infer real vendor block RAM, not a flip-flop-array fallback, on both Xilinx and
Lattice iCE40 toolchains. `tools/test_fpga.py` runs this as part of
`python3 tools/test_all.py` (skippable with `--quick`) and is the gate for the
project's "one config → FPGA and ASIC" claim.

## Method

For each config, `tools/test_fpga.py` runs yosys (`yowasp-yosys`):

```
read_verilog <name>.v
synth_xilinx -top <name> -run begin:map_ffram   # or synth_ice40
stat
```

and asserts the `stat` cell tally contains a real BRAM primitive
(`RAMB18E1`/`RAMB36E1` for Xilinx 7-series, `SB_RAM40_4K`/`SB_SPRAM256KA` for
iCE40) rather than a `$dff`/mux flip-flop array.

`-run begin:map_ffram` stops the synth flow right after the memory-mapping stage
(`memory_libmap` + the BRAM/LUTRAM techmap), before the LUT/ABC mapping stage for
the surrounding glue logic. That later stage is where this development machine's
`yowasp-yosys` (a WASM build of yosys) silently truncates output mid-pass with no
error — an environment quirk in the WASM build, not an RTL bug. Since BRAM cells
are fixed primitives ABC never touches or un-infers, stopping right after
memory-mapping is a faithful readout of whether the memory itself became a real
BRAM/SPRAM cell; it just skips the (broken, and irrelevant to this gate) step
that maps everything else to LUTs.

## Results

Matrix: all 3 SRAM kinds x byte-enable on/off, depth 256 (comfortably above the
distributed-RAM/BRAM threshold on every mainstream FPGA family) x width 32.

| Config | synth_xilinx | synth_ice40 |
|---|---|---|
| `sram_1rw`, 256x32 | 1x `RAMB18E1` | 2x `SB_RAM40_4K` |
| `sram_1rw`, 256x32, `--byte-en` | 1x `RAMB18E1` | 2x `SB_RAM40_4K` |
| `sram_1r1w`, 256x32 | 1x `RAMB18E1` | 2x `SB_RAM40_4K` |
| `sram_1r1w`, 256x32, `--byte-en` | 1x `RAMB18E1` | 2x `SB_RAM40_4K` |
| `sram_2r1w`, 256x32 | 2x `RAMB18E1` | 4x `SB_RAM40_4K` |
| `sram_2r1w`, 256x32, `--byte-en` | 2x `RAMB18E1` | 4x `SB_RAM40_4K` |

`sram_2r1w` costs double the BRAM primitives of `sram_1rw`/`sram_1r1w` because
neither Xilinx 7-series nor iCE40 offers a native two-independent-read-port block
RAM — yosys implements the second read port by duplicating the RAM (both copies
written identically, each serving one read port). Expected and correct; the RTL
itself has one write port and two read ports, as designed.

No RTL changes were needed to reach this result — Khnum's read-first,
synchronous-read, indexed-part-select-for-loop byte-write style (see
`khnum/rtl.py`'s emitters) already matches the structure both vendor
`memory_libmap` rulesets expect. This was verified, not assumed: `stat`'s cell
tally was inspected directly (see `tools/test_fpga.py`) rather than trusting a
"no error" exit code alone.

Not yet covered: `rf_2r1w_ff` and both FIFO kinds are excluded from this gate.
FIFOs and small flop-based register files are expected to stay flip-flop-based
(that's the whole point of `rf_2r1w_ff`'s <=64-depth cap) — BRAM inference is
an SRAM-only claim.
