# 𓃝 Khnum — the ram-headed god of memory

> *Khnum, the ram-headed creator god of ancient Egypt, shaped every being on his potter's wheel.
> This Khnum shapes every memory your silicon needs — on a laptop.*

**Khnum is a zero-dependency, laptop-class, open-source memory compiler.**
One command gives you verified, synthesizable RTL for SRAMs, register files, FIFOs,
ECC-protected memories and banked/tiled composites — each instance shipped **with its own
self-checking testbench, manifest, embedded formal proof (yosys+z3, vacuity-checked,
mutation-tested), and (roadmap) OpenROAD hardening recipe** — and the whole flow is
engineered to fit in **16 GB of RAM**.

<p align="center"><img src="docs/demo.gif" alt="Khnum terminal demo" width="700"/></p>

```
$ python3 -m khnum gen --kind sram_1rw --depth 1024 --width 32 --byte-en
khnum: wrote build/khnum_sram_1rw_1024x32_be.v
khnum: wrote build/khnum_sram_1rw_1024x32_be_tb.v
khnum: wrote build/khnum_sram_1rw_1024x32_be.manifest.json
khnum: khnum_sram_1rw_1024x32_be ready — 1024 words x 32 bits = 32 Kib, addr 10 bits, RDW read-first
```

No pip installs. No PDK downloads. No 64 GB build server. Python 3 standard library only.

---

## Why another memory compiler?

[OpenRAM](https://github.com/VLSIDA/OpenRAM) and [DFFRAM](https://github.com/AUCOHL/DFFRAM)
are excellent at what they do — generating SRAM macros for specific PDKs. Khnum occupies
a niche neither covers:

| | **Khnum** | OpenRAM | DFFRAM |
|---|---|---|---|
| Dependencies | **zero** (Python stdlib) | Python + packages + PDK setup | Python + packages |
| Memory kinds | **SRAM 1RW / 1R1W / 2R1W, flop register file, sync + async (CDC) FIFO, ECC SECDED, banked/tiled composites — all shipping today** | SRAM | RAM / register file |
| Self-checking TB per generated instance | ✅ always, automatically | partial | — |
| Lint-clean guarantee (`verilator -Wall`) | ✅ CI-enforced | — | — |
| Formal proof per instance | ✅ embedded in every SRAM/FIFO instance, discharged via yosys-smtbmc + z3, vacuity-checked, mutation-tested | — | — |
| ECC (SECDED) option | ✅ `--ecc` on any SRAM (single-correct, double-detect) | — | — |
| FPGA + ASIC from one config | ✅ portable RTL (BRAM-inference verified in P3) | ASIC only | ASIC only |
| PDK strategy | portable RTL + OpenROAD/ORFS hardening recipes (Sky130, ASAP7) — P4 | Sky130 / SCMOS / FreePDK45 | Sky130 |
| Runs comfortably on a 16 GB laptop | ✅ **hard design constraint** | heavy | moderate |

Khnum's bet: **most designs don't need a hand-crafted 6T bitcell macro** — they need
*correct, verified, portable* memories **right now**, that synthesize to BRAM on FPGA and
harden to standard-cell RAM through OpenROAD on ASIC, with proofs instead of promises.

## Quick start

```bash
git clone https://github.com/Lord1Egypt/Khnum
cd Khnum

# See what Khnum can shape
python3 -m khnum list

# Generate a 4 KiB byte-writable scratchpad
python3 -m khnum gen --kind sram_1rw --depth 1024 --width 32 --byte-en -o build

# Generate a 2-read-port register file memory
python3 -m khnum gen --kind sram_2r1w --depth 64 --width 64 -o build

# ECC-protect an SRAM (transparent SECDED: single-correct, double-detect)
python3 -m khnum gen --kind sram_1rw --depth 128 --width 32 --ecc -o build

# Tile a big array from small macros (4 depth banks x 2 width slices)
python3 -m khnum gen --kind sram_1r1w --depth 1024 --width 64 --bank-depth 4 --bank-width 2 -o build

# Prove everything works on your machine (needs verilator)
python3 tools/test_all.py
```

Every `gen` produces three artifacts:

| artifact | what it is |
|---|---|
| `<name>.v` | Verilog-2001 RTL — lint-clean under `verilator -Wall`, BRAM-inference friendly, read-first RDW |
| `<name>_tb.v` | self-checking randomized testbench (shadow-model golden reference, prints `KHNUM_TB_PASS`) |
| `<name>.manifest.json` | machine-readable record: ports, latency, semantics, views |

## Memory kinds (today)

| kind | ports | typical use |
|---|---|---|
| `sram_1rw` | 1 shared read/write, sync read | scratchpads, cache data arrays |
| `sram_1r1w` | 1 write + 1 read, sync read | queues, buffers, tag arrays |
| `sram_2r1w` | 1 write + 2 reads, sync read | register files, dual-issue reads |
| `rf_2r1w_ff` | 1 write + 2 **async** reads (flops, depth ≤ 64) | CPU register files, 0-cycle reads |
| `fifo_sync` | single-clock FIFO, FWFT, full/empty/level | pipeline buffers, elastic stages |
| `fifo_async` | dual-clock CDC FIFO, gray pointers + 2-FF sync | clock-domain crossings |

The three `sram_*` kinds support `--byte-en` (per-byte write lanes), depths 2 – 16M,
widths 1 – 4096, including non-power-of-two depths. Read-during-write returns **old data**
(read-first) — the one semantics that maps cleanly to Xilinx/Lattice BRAM *and*
standard-cell RAM.

**Modifiers on the SRAM kinds:**

- `--ecc` — wrap any SRAM in transparent Hamming **SECDED**: encode on write, decode +
  `single_err`/`double_err` flags on read. Single-bit errors are corrected, double-bit
  errors flagged. Fault-injection testbench proves every 1-bit and 2-bit error pattern.
- `--bank-depth N` / `--bank-width N` — tile one small base macro into a larger array:
  `--bank-depth` address-decodes N deep banks (with a registered read-select mux),
  `--bank-width` lane-concatenates N width slices, and the two compose into a grid. The
  wrapper keeps the **exact same ports** as a monolithic instance, so nothing downstream
  changes. Works on the SRAM kinds and the register file.

## Verification is the product

A memory generator you can't trust is worse than no generator. Khnum's rule:
**nothing ships unverified.**

- `tools/test_all.py` — full matrix: CLI hygiene, generation, manifest sanity,
  `verilator --lint-only -Wall` (zero warnings tolerated), Verilator simulation of every
  testbench (init sweep → randomized reads/writes with random byte masks → full readback).
- `tools/formal.py` — every SRAM/FIFO instance ships an embedded formal proof
  (yosys-smtbmc + z3): SRAM read-first (full-word AND per-byte-lane), FIFO occupancy
  never over/underflows, async-FIFO gray pointers stay valid gray encodings. Every proof
  is *vacuity-checked* — validated to actually contain assertions — and *mutation-tested*
  — we break the RTL on purpose and require the proof to fail.
- `tests/cocotb/` — one Python-driven cocotb suite per kind (`make CORE=<kind>`), each
  checking an independent golden model against real simulation — a third, unrelated
  verification method alongside the Verilog self-checking TB and the formal proofs.

## The 16 GB promise

Khnum is developed **on a 16 GB laptop, for 16 GB laptops**. Generation is O(KB) of text.
Simulation is Verilator. Hardening recipes (roadmap P4) are pre-tuned OpenROAD/ORFS
configurations validated to peak **below 14 GB**, so students, hobbyists and engineers in
the 99 % of the world without a server farm can go RTL → GDSII.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full phase plan with checklists, and
[STATUS.md](STATUS.md) for live progress.

- **P0 Genesis** ✅ — core compiler, 3 SRAM kinds, TB-per-instance, full test harness
- **P1 The Potter's Wheel** ✅ — flop register file, sync/async FIFOs (gray-coded CDC), ECC SECDED, banked/tiled composites
- **P2 The Proof** ✅ — cocotb suites (one per kind), formal properties (read-first,
  byte-lane, FIFO occupancy, gray-pointer) all non-vacuous and mutation-tested
- **P3 The FPGA Gate** — automated BRAM-inference verification (yosys synth_xilinx / synth_ice40)
- **P4 The Foundry** — OpenROAD/ORFS hardening recipes (Sky130 → ASAP7), 16 GB-safe, GDS gallery
- **P5 The Scribe** — characterization tables, docs site, terminal demo GIF
- **P6 Ascension** — v1.0.0: PyPI release, GitHub release, stability guarantees

## Project lineage

Khnum is part of the Lord1Egypt open-silicon pantheon:
[KemetCore](https://github.com/Lord1Egypt/KemetCore) (11 accelerators, RTL → 7 nm GDSII),
PtahCore (FP8 tensor accelerator), [Seshat](https://github.com/Lord1Egypt/Seshat)
(contract security scanner), [ThothTerm](https://github.com/Lord1Egypt/ThothTerm)
(GPU terminal). The formal-verification discipline here (vacuity checks, mutation-tested
proofs) was battle-tested across KemetCore's 11 cores.

## License

[Apache-2.0](LICENSE). Generated RTL is yours, unrestricted — Khnum places no license
requirements on its output.

---

*𓋹 Shaped on the potter's wheel. Verified before it leaves the workshop.*
