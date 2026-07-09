# 𓃝 Khnum — the ram-headed god of memory

> *Khnum, the ram-headed creator god of ancient Egypt, shaped every being on his potter's wheel.
> This Khnum shapes every memory your silicon needs — on a laptop.*

**Khnum is a zero-dependency, laptop-class, open-source memory compiler.**
One command gives you verified, synthesizable RTL for SRAMs, register files, FIFOs and
ECC-protected memories — each instance shipped **with its own self-checking testbench,
manifest, and (roadmap) formal proof and OpenROAD hardening recipe** — and the whole
flow is engineered to fit in **16 GB of RAM**.

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
| Memory kinds | SRAM 1RW / 1R1W / 2R1W today; register files, sync+async FIFOs, ECC SECDED, banked composites on the [roadmap](ROADMAP.md) | SRAM | RAM / register file |
| Self-checking TB per generated instance | ✅ always, automatically | partial | — |
| Lint-clean guarantee (`verilator -Wall`) | ✅ CI-enforced | — | — |
| Formal proof per instance | 🔜 roadmap P2 (yosys-smtbmc + z3, vacuity-checked) | — | — |
| ECC (SECDED) option | 🔜 roadmap P1 | — | — |
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
| `sram_1rw` | 1 shared read/write, sync read | scratchpads, caches data arrays |
| `sram_1r1w` | 1 write + 1 read, sync read | queues, buffers, tag arrays |
| `sram_2r1w` | 1 write + 2 reads, sync read | register files, dual-issue reads |

All kinds support `--byte-en` (per-byte write lanes), depths 2 – 16M, widths 1 – 4096,
including non-power-of-two depths. Read-during-write returns **old data** (read-first) —
the one semantics that maps cleanly to Xilinx/Lattice BRAM *and* standard-cell RAM.

## Verification is the product

A memory generator you can't trust is worse than no generator. Khnum's rule:
**nothing ships unverified.**

- `tools/test_all.py` — full matrix: CLI hygiene, generation, manifest sanity,
  `verilator --lint-only -Wall` (zero warnings tolerated), Verilator simulation of every
  testbench (init sweep → randomized reads/writes with random byte masks → full readback).
- Roadmap P2 adds **cocotb** suites and **formal proofs** (yosys-smtbmc + z3) with
  *vacuity checking* — every proof is validated to actually check assertions, and
  *mutation-tested* — we break the RTL on purpose and require the proof to fail.

## The 16 GB promise

Khnum is developed **on a 16 GB laptop, for 16 GB laptops**. Generation is O(KB) of text.
Simulation is Verilator. Hardening recipes (roadmap P4) are pre-tuned OpenROAD/ORFS
configurations validated to peak **below 14 GB**, so students, hobbyists and engineers in
the 99 % of the world without a server farm can go RTL → GDSII.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full phase plan with checklists, and
[STATUS.md](STATUS.md) for live progress.

- **P0 Genesis** ✅ — core compiler, 3 SRAM kinds, TB-per-instance, full test harness
- **P1 The Potter's Wheel** — register files, sync/async FIFOs (gray-coded CDC), ECC SECDED, banked/tiled composites
- **P2 The Proof** — cocotb suites, formal properties + non-vacuous mutation-tested proofs
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
