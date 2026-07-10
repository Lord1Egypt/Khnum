# Khnum Roadmap — the path to the top open-source memory project

Rules of this file:
- A box is checked **only** when `python3 tools/test_all.py` exits 0 with the feature
  covered by at least one matrix entry, and the work is **merged to main via PR**.
- "Partial" is not "done". Never check a box for scaffolding.
- Every phase ends with a checkpoint commit updating this file + STATUS.md.

---

## P0 — Genesis ✅ (completed 2026-07-10)

- [x] Package skeleton (`khnum/`), zero dependencies, Python 3 stdlib only
- [x] `Config` validation (depth 2–2^24, width 1–4096, byte-en requires width%8==0)
- [x] RTL emitters: `sram_1rw`, `sram_1r1w`, `sram_2r1w` (Verilog-2001, read-first,
      byte-enable lanes, non-power-of-2 depths)
- [x] Self-checking TB emitter per instance (shadow model, init sweep + random phase +
      final sweep, `KHNUM_TB_PASS` protocol)
- [x] Manifest JSON per instance
- [x] Non-blocking CLI (`gen`, `list`, `--version`), argparse, exit codes
- [x] `tools/test_all.py`: CLI hygiene + 7-config matrix × (gen, manifest, lint -Wall
      zero-warning, Verilator --binary --timing sim) — **ALL GREEN**
- [x] README, ROADMAP, STATUS, CLAUDE.md handoff, LICENSE (Apache-2.0), CONTRIBUTING

## P1 — The Potter's Wheel (memory suite) ✅ (completed 2026-07-10)

Goal: Khnum generates every on-chip memory a real SoC needs, not just SRAM.

- [x] `rf_2r1w_ff`: flop-based register file with **asynchronous** read (combinational
      rdata), for depths ≤ 64 — the CPU-register-file workhorse (PR #2)
- [x] `fifo_sync`: single-clock FIFO (FWFT, full/empty/level; TB covers full & empty
      boundaries, ignored ops, simultaneous push/pop) (PR #2)
- [x] `fifo_async`: dual-clock FIFO — gray-coded pointers (Cummings), 2-FF synchronizers;
      TB with coprime #7/#11 clocks, 2000-word order check, watchdog (PR #2)
- [x] `ecc_secded`: Hamming SECDED encode/decode modules + `--ecc` wrapper option on
      sram kinds (data widths 4–1024, incl. 8/32/64; single-error corrected, double-error
      detected; standalone TB injects **all** 1-bit and **all** 2-bit faults ×25 trials
      and checks correction/detection flags) (PR #3)
- [x] Banking composer: `--bank-depth N` / `--bank-width N` emit a wrapper that tiles one
      deterministic base macro (address-decode deep tiling + registered read-select mux,
      lane-concat wide tiling, composable into a grid); identical external ports so the
      standard TB drives it; manifest lists the hierarchy (`children` + `banking`) (PR #4)
- [x] Extend `tools/test_all.py` matrix to cover every new kind/option: **16 configs +
      7 banked + 3 standalone ECC + CLI hygiene**, all lint -Wall zero-warning (PR #4)
- [x] README: RF / FIFO / ECC / banking moved from "roadmap" to shipped honestly (PR #4)

## P2 — The Proof (verification-first)

Goal: Khnum's headline differentiator — proofs, not promises.

- [ ] cocotb testbenches (`tests/cocotb/`), SIM=verilator, one suite per kind —
      mirror KemetCore's proven Makefile pattern
- [ ] Formal properties embedded in generated RTL under `` `ifdef FORMAL `` (no `bind` —
      yosys 0.6x has none): rdata matches a golden shadow process, write lanes only
      change masked bytes, FIFO never overflows/underflows, gray pointers change 1 bit
      — **partial (PR #5): SRAM read-first scoreboard shipped on all 3 sram kinds
      (full-word writes); byte-lane masks + FIFO over/underflow + gray-pointer props pending**
- [x] `tools/formal.py`: runs yowasp-yosys → `async2sync` → `write_smt2` → yowasp-yosys-smtbmc
      (z3). **Vacuity enforced**: counts `yosys-smt2-assert` in the SMT2; 0 assertions = FAIL.
      Proves 4 SRAM configs; yosys runs cwd=outdir (WASI sandbox) (PR #5)
- [x] Mutation testing: `tools/mutate.py` breaks read-first (read→write-through) per kind
      and `formal.py` REQUIRES the proof to fail; a mutation that survives fails the run (PR #5)
- [x] CI: GitHub Actions `.github/workflows/ci.yml` — ubuntu-latest, apt verilator, pip
      yowasp-yosys + z3-solver, runs `tools/test_all.py` (matrix + formal) on push/PR (PR #5)

## P3 — The FPGA Gate

Goal: prove the "one config → FPGA and ASIC" claim mechanically.

- [ ] `tools/test_fpga.py`: run yowasp-yosys `synth_xilinx` and `synth_ice40` on each
      generated SRAM; parse the report; **require BRAM/SPRAM inference** (RAMB18/36 or
      SB_RAM40_4K / SPRAM cells present, zero flip-flop-array fallback for depths ≥ 256)
- [ ] Fix any inference blockers found (init values, enable structure) without breaking
      the P0/P1 test matrix
- [ ] Document per-kind inference results in `docs/FPGA.md`

## P4 — The Foundry (ASIC hardening, 16 GB-safe)

Goal: DFFRAM-style standard-cell hardening through OpenROAD/ORFS with recipes that
peak < 14 GB RSS (16 GB laptop with WSL2 headroom — see CLAUDE.md memory rules).

- [ ] `harden/` directory: ORFS config per showcase size (e.g. 256×32, 1K×32, 2K×64)
      for **sky130hd** using the local Docker openroad/orfs image (same as KemetCore
      `flow/harden.sh` pattern)
- [ ] `tools/harden.sh`: wraps Docker with `--memory=13g --memory-swap=24g`
      (Docker-swap OOM lesson) and produces GDS + DEF + reports into `harden/results/`
- [ ] Record peak RSS per recipe; any recipe > 14 GB must be re-tuned (smaller
      utilization, routing effort) — the 16 GB promise is a release gate
- [ ] GDS gallery in `docs/GALLERY.md` (screenshots via ORFS klayout export)
- [ ] Stretch: ASAP7 variants (KemetCore flow already proves local ASAP7 works)
- [ ] Liberty/LEF abstract stubs emitted alongside GDS for SoC integration

## P5 — The Scribe (docs, demo, characterization)

- [ ] `docs/CHARACTERIZATION.md`: area/timing tables per size from ORFS reports,
      auto-generated by `tools/characterize.py`
- [ ] **Terminal demo GIF (MANDATORY house rule)**: VHS tape in `docs/demo.tape`,
      GIF embedded at the top of README — every Lord1Egypt CLI project has one
- [ ] gh-pages landing site (same pattern as KemetCore's)
- [ ] `docs/INTEGRATION.md`: how to drop Khnum memories into a SoC (KemetCore cores as
      worked examples)

## P6 — Ascension (v1.0.0)

- [ ] `pyproject.toml` finalized; publish **khnum-ram** to PyPI (token in
      `~/.skillforge_tokens`; follow Seshat's release playbook)
- [ ] `pip install khnum-ram` → `khnum` console script works
- [ ] GitHub Release v1.0.0 with changelog
- [ ] README final pass: every claim true, comparison table updated, demo GIF live
- [ ] Announce-ready: repo About, topics, social preview

---

## Checkpoint protocol (for every phase)

1. Branch `feat/<phase-item>` → implement → `python3 tools/test_all.py` exits 0.
2. Update ROADMAP checkboxes + STATUS.md "RESUME HERE" block **in the same PR**.
3. PR → merge (Co-Authored-By trailer for Pair Extraordinaire) → delete branch.
4. Never leave main red. Never claim a box that test_all doesn't prove.
