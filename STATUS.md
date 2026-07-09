# Khnum — live status tracker

## ▶▶ RESUME HERE (updated 2026-07-10)

- **Phase:** P0 Genesis ✅ COMPLETE — next is **P1 The Potter's Wheel**.
- **Next task:** implement `rf_2r1w_ff` (flop-based register file, ASYNC read,
  depth ≤ 64) per CLAUDE.md "P1" spec: emitter in `khnum/rtl.py`, TB in `khnum/tb.py`,
  CLI kind added, ≥ 2 new matrix entries in `tools/test_all.py`, all green, PR.
- **Baseline health:** `python3 tools/test_all.py` → `ALL GREEN (7 configs + CLI hygiene)`
  on 2026-07-10 (Verilator 5.020, Python 3.13).
- **Branch state:** main clean, no open PRs.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 9/9 boxes, test-proven |
| P1 Potter's Wheel | ⬜ 0/7 |
| P2 The Proof | ⬜ 0/5 |
| P3 FPGA Gate | ⬜ 0/3 |
| P4 The Foundry | ⬜ 0/6 |
| P5 The Scribe | ⬜ 0/4 |
| P6 Ascension | ⬜ 0/5 |

**Total: 9/39 (23%) — "partial" ≠ "done".**

## Session log

- **2026-07-10** — Genesis. Full P0: package, 3 SRAM kinds (1RW/1R1W/2R1W, byte-en,
  non-pow2 depths), TB-per-instance with shadow-model checking, manifests, CLI,
  test_all harness (7 configs, lint -Wall zero-warning, Verilator sim). One template
  bug found & fixed (unescaped `%` in 2r1w TB — see CLAUDE.md rule 6). Docs suite,
  repo created, About/topics set.
