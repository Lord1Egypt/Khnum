# Khnum — live status tracker

## ▶▶ RESUME HERE (updated 2026-07-10, session 6)

- **Phase:** P2 The Proof — ✅ **CLOSED 5/5** (PR #6, this session: byte-lane formal +
  FIFO formal properties + cocotb suites, on top of PR #5's formal spine). P1 = ✅ 7/7
  (PRs #2–#4).
- **Next task: P3 FPGA Gate** (`tools/test_fpga.py`: `yowasp-yosys -p "read_verilog x.v;
  synth_xilinx -top <name>; stat"` → assert `RAMB18E1|RAMB36E1` for depths ≥ 256, and
  `synth_ice40` → `SB_RAM40_4K`/SPRAM. If inference fails: check reset-on-rdata / read-enable
  structure in the emitters first.). Then P4 hardening (Docker `--memory=13g
  --memory-swap=24g`), P5 docs+VHS demo GIF, P6 PyPI `khnum-ram`. All per CLAUDE.md.
- **KEY formal facts learned (PR #5+#6):** yowasp-yosys runs in a **WASI sandbox — only
  sees its cwd**, so `formal.py`/tools must invoke it with `cwd=outdir` and bare filenames
  (absolute paths → "file not found"). `async2sync` before `write_smt2` is mandatory (else
  0 assertions). The read-first scoreboard uses `(* anyconst *)` symbolic address; BMC
  depth 14–15 with z3 proves full-word configs in seconds. **Byte-lane configs need a
  per-lane `f_valid`/`f_exp` vector** (naive full-word model provably fails on `--byte-en`)
  AND a much shorter BMC depth (~6) — z3 solves per-lane part-selects far slower with
  unroll depth, but read-first shows within 2 cycles so depth 6 is still sound. **FIFO
  proofs need `initial assume(!rst_n)`** (else BMC starts from an arbitrary non-reset state
  where occupancy invariants are trivially false) — same for both `wrst_n`/`rrst_n` in
  fifo_async.
- **KEY cocotb env gotcha (PR #6, this machine only)**: conda's `PYTHONHOME` export
  (cocotb's `Makefile.inc` sets it for its own embedded interpreter) collides with
  Verilator's separate, hardcoded `/usr/bin/python3` call during the C++ build step →
  `ModuleNotFoundError: No module named 'encodings'`. Fix: override Verilator's `PYTHON3`
  make var to strip just that one call's env: `make CORE=<kind> PYTHON3='env -u
  PYTHONHOME /usr/bin/python3'`. A venv does NOT fix this (`cocotb-config`'s shebang is
  hardcoded to the conda interpreter, bypassing venv detection). See ROADMAP.md P2 for
  the full note. CI (fresh Ubuntu, no conda) should not need this override.
- **Baseline health:** `python3 tools/test_all.py` → `ALL GREEN (16 configs + 7 banked +
  3 ECC pairs + CLI hygiene + formal proofs)` — **173 checks, 0 fail** — 2026-07-10
  (Verilator 5.020, yosys 0.66, z3 4.16, Python 3.13). `--quick` skips formal. `formal.py`
  standalone now proves **9 configs** (was 4). All 6 `tests/cocotb/` suites pass
  standalone via `make CORE=<kind> PYTHON3='env -u PYTHONHOME /usr/bin/python3'`
  (not yet wired into `test_all.py`/CI — see ROADMAP.md note on why).
- **Branch state:** `feat/p2-formal-extend`, PR #6 — see PR for merge state.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 9/9 boxes, test-proven |
| P1 Potter's Wheel | ✅ 7/7, test-proven |
| P2 The Proof | ✅ 5/5, test-proven |
| P3 FPGA Gate | ⬜ 0/3 |
| P4 The Foundry | ⬜ 0/6 |
| P5 The Scribe | ⬜ 0/4 |
| P6 Ascension | ⬜ 0/5 |

**Total: 21/39 (54%) — "partial" ≠ "done".**

## Session log

- **2026-07-10 (session 6, PR #6)** — P2 CLOSED 5/5. Extended `khnum/rtl.py`'s formal
  scoreboard with `_formal_sram_be`: per-byte-lane `f_valid`/`f_exp` tracking so
  `--byte-en` SRAM configs get a genuine (non-vacuous) read-first proof instead of being
  skipped. Added FIFO safety properties under `` `ifdef FORMAL ``: `fifo_sync` proves
  occupancy never exceeds depth (`initial assume(!rst_n)` + `assert(count<=DEPTH)`);
  `fifo_async` proves both gray registers stay valid gray encodings of their binary
  counters (`wgray == (wbin>>1)^wbin`, same for read side) — the property the CDC 2-FF
  synchronizers rely on. `tools/mutate.py` gained kind-specific mutations for both FIFO
  kinds (fixed an off-by-one in the fifo_async bit-width substitution caught by the
  formal run itself: emitter uses `pw-1` as the MSB index, not `pw`). `tools/formal.py`
  matrix grew 4→9 configs (byte-lane SRAM ×3 at BMC depth 6, both FIFO kinds at depth
  15); `prove()` now takes a dict-entry so per-config BMC depth and kind-specific kwargs
  are clean. Built `tests/cocotb/`: Makefile generates a fixed-name `dut` module on the
  fly per kind (`python3 -m khnum gen --name dut`), one test file per kind driving an
  independent Python golden model — a third, unrelated verification method. Found and
  fixed a real cocotb bug during first runs: writing to a DUT signal immediately after
  an `await ReadOnly()` sample (with no intervening time-advancing trigger) raises
  "scheduled during a read-only sync phase" — fixed by inserting `await NextTimeStep()`
  between every ReadOnly-based sample and the next write, in all 6 suites. All 6 pass
  standalone. `python3 tools/test_all.py` still ALL GREEN (173 checks) — no regression.

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
