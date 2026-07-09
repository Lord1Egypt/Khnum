# CLAUDE.md — Khnum assistant handoff (READ THIS FIRST, ENTIRELY)

You are continuing **Khnum**, Lord1Egypt's open-source memory compiler, designed by a
larger model that has since handed off. This file tells you EXACTLY what to do and how.
Do not improvise around these rules — they encode hard-won lessons from KemetCore and
PtahCore. When in doubt, do the smaller, verifiable thing.

## Mission

Make Khnum the #1 open-source memory-compiler project: a zero-dependency, laptop-class
generator of **verified** SRAM / register-file / FIFO / ECC RTL with formal proofs and
16 GB-safe OpenROAD hardening. Honesty is the brand: **a checked box that isn't true
destroys the project.**

## Where things stand — start here every session

1. Read `STATUS.md` (the ▶▶ RESUME HERE block) — it says the exact next task.
2. Read `ROADMAP.md` for the current phase's checklist and acceptance criteria.
3. Run `python3 tools/test_all.py` — it MUST exit 0 before you change anything.
   If it doesn't, fixing that is your only task.

## Non-negotiable rules

1. **Zero dependencies.** `khnum/` uses Python 3 stdlib ONLY (`argparse`, `json`, `os`,
   `math`, `subprocess` in tools). Never add a pip dependency to the generator. Dev
   tools (cocotb, yowasp-yosys) live in tools/tests only, never imported by `khnum/`.
2. **Test gate.** A task is done only when `python3 tools/test_all.py` exits 0 AND the
   new feature has matrix coverage in it. New kinds/options = new matrix entries.
3. **Lint gate.** Generated DUT RTL must pass `verilator --lint-only -Wall` with ZERO
   warnings. Testbenches may warn (they're built with `-Wno-fatal`), DUTs may not.
4. **Non-blocking CLI.** Never call `input()`. Everything flag-driven, proper exit codes
   (0 ok, 2 config error). Automation must never hang.
5. **Generated RTL rules** (see `khnum/rtl.py` docstring): Verilog-2001 only in DUTs,
   ONE `always` block per memory array (Verilator rejects multi-driven memories),
   read-first RDW semantics, byte writes via indexed part-select for-loop.
   SystemVerilog is allowed ONLY inside `` `ifdef FORMAL `` blocks (P2).
6. **Template escaping**: emitters use `%`-formatting — every literal `%` in Verilog
   (e.g. `$urandom % DEPTH`) must be written `%%` in the Python template. This already
   caused one P0 bug. `grep` for lone `%` when a gen step dies with
   "unsupported format character".
7. **Git workflow (house rule)**: branch → PR → merge, NEVER direct push to main.
   Commit messages end with the Co-Authored-By trailer. Push immediately after every
   merge-worthy unit of work. Update ROADMAP.md checkboxes + STATUS.md in the same PR
   as the feature.
8. **Honest docs.** Never advertise an unimplemented feature as existing. README's
   comparison table marks unshipped things as "roadmap". When you ship one, move it.
9. **16 GB laptop.** Mohamed's machine has 16 GB RAM under WSL2 (~13.8 GB usable).
   Any flow step that could exceed ~13 GB must run in Docker with
   `--memory=13g --memory-swap=24g` (swap absorbs the spike; do NOT raise the WSL
   memory cap — it freezes Windows). This applies to P4 hardening especially.

## Environment map (this machine)

| tool | where | notes |
|---|---|---|
| python3 | 3.13, `~/miniconda3/bin/python3` | |
| verilator | `/usr/bin/verilator` 5.020 | sim + lint; `--binary --timing` builds TBs |
| cocotb | 1.9.2 (pip) | use `SIM=verilator` Makefiles like `KemetCore/projects/*/rtl/tb/Makefile` |
| yosys | `yowasp-yosys` (pip, WASM) | also `yowasp-yosys-smtbmc` for formal with z3 |
| OpenROAD/ORFS | local Docker image (see `KemetCore/flow/harden.sh`) | P4 only |
| gh CLI | authenticated as Lord1Egypt | use for PRs |

## Verification commands

```bash
python3 tools/test_all.py            # full gate — must exit 0
python3 -m khnum gen --kind sram_1rw --depth 64 --width 32 --byte-en -o build/x   # manual poke
cd build/x && verilator --binary --timing -j 2 -Wno-fatal --top <name>_tb <name>.v <name>_tb.v -o sim && ./obj_dir/sim
```

A passing sim prints `KHNUM_TB_PASS`. Anything else is a failure — including silence.

## FORMAL VERIFICATION GOTCHAS (from KemetCore — memorize)

- **ALWAYS run `async2sync` before `write_smt2`** in yosys. Without it, `$check` cells
  are silently dropped and your "proof" checks NOTHING (this exact vacuity bug shipped
  8 fake proofs in KemetCore before being caught).
- **Vacuity check is mandatory**: after `write_smt2`, count assertions in the .smt2
  output; 0 assertions = the proof is vacuous = FAIL the run.
- **Mutation-test every proof**: deliberately break the RTL (flip an operator), rerun,
  and require the proof to fail. A proof that can't catch a planted bug is decoration.
- Embed properties via `` `ifdef FORMAL `` inside the generated module — yosys 0.6x has
  **no `bind`** and no hierarchical references.
- z3 cannot prove floating-point adder/divider equivalence miters — irrelevant for
  memories, but don't try clever FP tricks.

## Phase task specs (do them in order; each is one or more PRs)

### P1 — The Potter's Wheel
Work through the ROADMAP P1 boxes top-to-bottom. Concrete guidance:
- `rf_2r1w_ff`: async read = `assign rdata0 = mem[raddr0];` — this is the ONE kind with
  combinational read. Depth cap 64, error above it (flops are expensive).
- `fifo_sync`: classic count-based; expose `full`, `empty`, `level[$clog2(D):0]`.
  TB must test: fill to full, drain to empty, push@full ignored, pop@empty ignored,
  simultaneous push+pop at every occupancy.
- `fifo_async`: gray-code pointers, 2-FF synchronizers, standard Cummings architecture.
  TB: two `always #N` clocks with coprime periods (e.g. #7/#11), 10k+ random ops,
  data integrity through a shadow queue (model FIFO order, not addresses).
- `ecc_secded`: encode = data + Hamming parity + overall parity; decode outputs
  `corrected_data`, `single_err`, `double_err`. Wrapper option `--ecc` wraps sram kinds
  (stored width = data + ecc bits; manifest records both). TB injects faults by XORing
  the DUT's stored word via writes of pre-corrupted codewords through a raw port or by
  generating the encoder/decoder standalone tests first (simpler: standalone TB for
  enc→corrupt→dec across all 1-bit and sampled 2-bit error positions).
- Banking composer: pure wrapper emission — generate K base macros + decode/mux glue.
  Keep base macro names deterministic. Manifest gains `"children": [...]`.
- After EVERY kind: extend the matrix in `tools/test_all.py`, run it, update ROADMAP.

### P2 — The Proof
- Mirror `KemetCore/projects/racore/rtl/tb/Makefile` for cocotb+verilator.
- `tools/formal.py` flow per instance:
  `yowasp-yosys -p "read_verilog -formal -DFORMAL x.v; prep -top <name>; async2sync; write_smt2 x.smt2"`
  then `yowasp-yosys-smtbmc -s z3 --bmc/-i` for BMC + induction. Enforce the vacuity
  count. Add `tools/mutate.py`. Wire both into test_all (skippable via `--quick` flag
  if runtime > 5 min).
- GitHub Actions workflow `.github/workflows/ci.yml`: ubuntu-latest,
  `apt-get install verilator`, `pip install yowasp-yosys`, run test_all.

### P3 — The FPGA Gate
- `yowasp-yosys -p "read_verilog x.v; synth_xilinx -top <name>; stat"` → assert
  `RAMB18E1|RAMB36E1` in stat output for depths ≥ 256 (and `SB_RAM40_4K`/SPRAM for
  synth_ice40). If inference fails, the usual culprits: reset on rdata, read enable
  structure. Fix emitters, keep test_all green.

### P4 — The Foundry
- Copy the working pattern from `KemetCore/flow/harden.sh` + its ORFS Docker usage.
- Start with sky130hd, one small size (256×32). Set Docker
  `--memory=13g --memory-swap=24g`. Record peak RSS (`docker stats` sampling) into the
  recipe file. Only then scale up sizes. If detail route OOMs, reduce
  `CORE_UTILIZATION` / increase die area before anything else.
- Ship: config.mk per size, harden.sh wrapper, results table, GDS gallery doc.

### P5 — The Scribe
- VHS demo GIF is a HOUSE RULE (docs/demo.tape → GIF at top of README). Install vhs or
  use asciinema+agg fallback (`~/agg` exists).
- gh-pages: copy KemetCore's landing-page pattern.

### P6 — Ascension
- Follow Seshat's PyPI playbook (memory: `project_seshat.md`); token in
  `~/.skillforge_tokens`. Package name `khnum-ram`, console script `khnum`.
- Only release when every README claim is mechanically true.

## When you finish ANY session

1. `python3 tools/test_all.py` exits 0.
2. ROADMAP.md boxes + STATUS.md RESUME block updated.
3. Branch pushed, PR opened (or merged if authorized), nothing uncommitted.
4. Tell Mohamed plainly what is done, what is not, and what's next. Honest > flattering.
