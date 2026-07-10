# Khnum — live status tracker

## ▶▶ RESUME HERE (updated 2026-07-10)

- **Phase:** P1 The Potter's Wheel — ✅ **7/7 COMPLETE** (rf_2r1w_ff + fifo_sync +
  fifo_async in PR #2; `ecc_secded` in PR #3; banking composer + matrix ≥16 + README
  honesty pass in PR #4).
- **Next task:** **Start P2 — The Proof.** Per repo CLAUDE.md "P2" spec: (1) cocotb
  suites under `tests/cocotb/` mirroring `KemetCore/projects/racore/rtl/tb/Makefile`
  (SIM=verilator), one per kind; (2) formal properties embedded via `` `ifdef FORMAL ``
  in the emitters (no `bind` in yosys 0.6x) — rdata==golden shadow, byte lanes only touch
  masked bytes, FIFO never over/underflows, gray pointers change 1 bit; (3) `tools/formal.py`
  = `read_verilog -formal -DFORMAL` → `prep` → **`async2sync` (MANDATORY)** → `write_smt2`
  → smtbmc z3, with a **vacuity assertion count** (0 asserts = FAIL) and `tools/mutate.py`
  mutation testing; (4) `.github/workflows/ci.yml`. Add a `--quick` flag to test_all if
  formal runtime > 5 min.
- **Baseline health:** `python3 tools/test_all.py` → `ALL GREEN (16 configs + 7 banked +
  3 ECC pairs + CLI hygiene)` — 172 checks, 0 fail — on 2026-07-10 (Verilator 5.020,
  Python 3.13).
- **Branch state:** main clean after PR #4.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 9/9 boxes, test-proven |
| P1 Potter's Wheel | ✅ 7/7, test-proven |
| P2 The Proof | ⬜ 0/5 |
| P3 FPGA Gate | ⬜ 0/3 |
| P4 The Foundry | ⬜ 0/6 |
| P5 The Scribe | ⬜ 0/4 |
| P6 Ascension | ⬜ 0/5 |

**Total: 16/39 (41%) — "partial" ≠ "done".**

## Session log

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
