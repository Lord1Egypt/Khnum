# Khnum — live status tracker

## ▶▶ RESUME HERE (updated 2026-07-10)

- **Phase:** P1 The Potter's Wheel — 3/7 boxes (rf_2r1w_ff + fifo_sync + fifo_async
  shipped in PR #2).
- **Next task:** `ecc_secded` per CLAUDE.md "P1" spec — standalone
  `khnum_secded_enc/dec_{8,16,32,64}` combinational modules (`khnum/ecc.py`, own `ecc`
  CLI subcommand), fault-injection TB (all 1-bit positions corrected + sampled 2-bit
  detected), then `--ecc` wrapper option on sram kinds. After that: banking composer,
  then matrix ≥ 16 + README honesty pass to close P1.
- **Baseline health:** `python3 tools/test_all.py` → `ALL GREEN (13 configs + CLI
  hygiene)` on 2026-07-10 (Verilator 5.020, Python 3.13).
- **Branch state:** main clean after PR #2.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 9/9 boxes, test-proven |
| P1 Potter's Wheel | 🔧 3/7 |
| P2 The Proof | ⬜ 0/5 |
| P3 FPGA Gate | ⬜ 0/3 |
| P4 The Foundry | ⬜ 0/6 |
| P5 The Scribe | ⬜ 0/4 |
| P6 Ascension | ⬜ 0/5 |

**Total: 12/39 (31%) — "partial" ≠ "done".**

## Session log

- **2026-07-10 (session 2, PR #2)** — P1 first wave: `rf_2r1w_ff` (async-read flop RF,
  depth cap 64), `fifo_sync` (FWFT, count-based, flags+level checked every op),
  `fifo_async` (Cummings gray/2-FF CDC, pow2-depth guard, coprime-clock TB + watchdog).
  Matrix 7→13 configs + 3 new rejection checks. ALL GREEN, zero lint warnings.

- **2026-07-10** — Genesis. Full P0: package, 3 SRAM kinds (1RW/1R1W/2R1W, byte-en,
  non-pow2 depths), TB-per-instance with shadow-model checking, manifests, CLI,
  test_all harness (7 configs, lint -Wall zero-warning, Verilator sim). One template
  bug found & fixed (unescaped `%` in 2r1w TB — see CLAUDE.md rule 6). Docs suite,
  repo created, About/topics set.
