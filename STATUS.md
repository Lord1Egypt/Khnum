# Khnum — live status tracker

## ▶▶ RESUME HERE (updated 2026-07-10)

- **Phase:** P2 The Proof — 🔧 **3/5** (formal spine shipped in PR #5: `tools/formal.py`
  with mandatory vacuity count, `tools/mutate.py`, CI workflow, and SRAM read-first
  proofs). P1 = ✅ 7/7 (PRs #2–#4).
- **Next task (continue P2):** (1) **Extend formal properties** — the two open sub-parts
  of the "formal properties" box: byte-lane masks (per-lane valid tracking in the
  scoreboard — the naive full-word model FAILS on `--byte-en`, confirmed in scratchpad)
  and the FIFO properties (never over/underflow via a symbolic occupancy invariant;
  gray pointers change exactly 1 bit). Add each to `khnum/fifo.py` + rf under
  `` `ifdef FORMAL `` and to `FORMAL_MATRIX`. (2) **cocotb suites** under `tests/cocotb/`,
  SIM=verilator, mirroring `KemetCore/projects/racore/rtl/tb/Makefile`, one per kind.
- **KEY formal facts learned (PR #5):** yowasp-yosys runs in a **WASI sandbox — only sees
  its cwd**, so `formal.py`/tools must invoke it with `cwd=outdir` and bare filenames
  (absolute paths → "file not found"). `async2sync` before `write_smt2` is mandatory (else
  0 assertions). The read-first scoreboard uses `(* anyconst *)` symbolic address; BMC
  depth 14–15 with z3 proves in seconds. Byte-en needs per-lane `f_valid`.
- **Baseline health:** `python3 tools/test_all.py` → `ALL GREEN (16 configs + 7 banked +
  3 ECC pairs + CLI hygiene + formal proofs)` — **173 checks, 0 fail** — 2026-07-10
  (Verilator 5.020, yosys 0.66, z3 4.16, Python 3.13). `--quick` skips formal.
- **Branch state:** main clean after PR #5.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 9/9 boxes, test-proven |
| P1 Potter's Wheel | ✅ 7/7, test-proven |
| P2 The Proof | 🔧 3/5 |
| P3 FPGA Gate | ⬜ 0/3 |
| P4 The Foundry | ⬜ 0/6 |
| P5 The Scribe | ⬜ 0/4 |
| P6 Ascension | ⬜ 0/5 |

**Total: 19/39 (49%) — "partial" ≠ "done".**

## Session log

- **2026-07-10 (session 5, PR #5)** — P2 formal spine. `tools/formal.py`:
  yosys `read_verilog -formal -DFORMAL` → `prep` → **`async2sync`** → `write_smt2`, with a
  mandatory vacuity count (`yosys-smt2-assert` ≥ 1) then z3 smtbmc; proves the read-first
  property on 4 SRAM configs (all 3 kinds). Embedded `` `ifdef FORMAL `` symbolic-address
  scoreboard in the sram emitters (full-word writes only). `tools/mutate.py` breaks
  read-first → `formal.py` requires the proof to FAIL (non-vacuity, mutation-caught).
  `.github/workflows/ci.yml` runs the whole gate on push/PR. test_all runs formal by
  default (`--quick` skips). 173 checks, 0 fail. Learned: yowasp-yosys is WASI-sandboxed
  to its cwd.

- **2026-07-10 (session 4, PR #4)** — P1 CLOSED. Banking composer (`khnum/bank.py`):
  `--bank-depth N` (pow2, high-address decode + registered read-select mux for the sync
  kinds, live mux for the async rf) / `--bank-width N` (lane-concat), composable into a
  D×W grid, tiling one deterministic `<name>_mac` base macro. Wrapper keeps identical
  external ports so the standard TB drives it unchanged. Verified on all 3 sram kinds +
  rf, deep/wide/grid. test_all +7 banked configs + 4 banking hygiene rejections (172
  checks, 0 fail). README honesty pass: RF/FIFO/ECC/banking all moved to "shipped".

- **2026-07-10 (session 3, PR #3)** — P1 `ecc_secded`: Hamming SECDED encoder/decoder
  emitters (`khnum/ecc.py`), standalone `khnum ecc --width K` pair + fault-injection TB
  (every 1-bit flip corrected, every 2-bit pair flagged double_err, ×25 random trials),
  and transparent `--ecc` wrapper on all 3 sram kinds (encode-on-write, decode+flags
  on read; 2r1w gets one decoder per read port). Manifest records `ecc{scheme,
  data_width,code_width}` + `children`. test_all rewritten to glob multi-file ECC
  hierarchies: matrix 13→16 configs + 3 standalone ECC widths (8/32/64) + 2 new hygiene
  rejections (`--ecc`+`--byte-en`, `--ecc` on fifo). ALL GREEN, zero DUT lint warnings.

- **2026-07-10 (session 2, PR #2)** — P1 first wave: `rf_2r1w_ff` (async-read flop RF,
  depth cap 64), `fifo_sync` (FWFT, count-based, flags+level checked every op),
  `fifo_async` (Cummings gray/2-FF CDC, pow2-depth guard, coprime-clock TB + watchdog).
  Matrix 7→13 configs + 3 new rejection checks. ALL GREEN, zero lint warnings.

- **2026-07-10** — Genesis. Full P0: package, 3 SRAM kinds (1RW/1R1W/2R1W, byte-en,
  non-pow2 depths), TB-per-instance with shadow-model checking, manifests, CLI,
  test_all harness (7 configs, lint -Wall zero-warning, Verilator sim). One template
  bug found & fixed (unescaped `%` in 2r1w TB — see CLAUDE.md rule 6). Docs suite,
  repo created, About/topics set.
