# Khnum — live status tracker

## ▶▶ SESSION 8 UPDATE (2026-07-13) — 2048x64 PLATEAUED at 1 antenna violation after 3 attempts; paused for a design-level fix

Three tuning attempts on `khnum_sram_1rw_2048x64`, each ~19-24h wall time,
all via `bash tools/harden.sh khnum_sram_1rw_2048x64` in Docker
(`openroad/orfs:latest`, `--memory=13g --memory-swap=24g`):

| attempt | clock | antenna caps (GRT/DRT) | route DRC | WNS/TNS | antenna signoff |
|---|---|---|---|---|---|
| 1 | 8.0ns | 5/5 (default) | 0 | -0.48/-0.92 (NOT closed) | 10 violations |
| 2 | 8.5ns | 10/5 | 0 | 0.00/0.00 (closed) | 1 (grt) + 1 (drt) |
| 3 | 8.5ns | 20/10 | 0 | 0.00/0.00 (closed, slack +0.40) | 0 (grt) + 1 (drt) |

**Timing and routing are both genuinely closed as of attempt 2.** Only
antenna signoff remains open, and it has plateaued on a single DRT-level
violation (met4 side-area ratio) that keeps landing on a similar
high-fanout clock-buffer-driven net (`clkdlybuf4s50` in both attempts 2 and
3, different net each time) despite doubling the repair-iteration cap twice
(5→10→20). **Diminishing returns confirmed — raising the cap further is
unlikely to be the fix**; this looks like it needs a targeted lever instead
(bigger/extra antenna diode cell near that specific net, or CTS-level net
splitting), not another blind ~20h cap-bump run.

**Decision (Mohamed, 2026-07-13): pause further attempts here rather than
keep burning multi-hour Docker runs chasing one violation** — GDS from
attempt 3 (`harden/results/.../6_final.gds`, WNS 0.00/TNS 0.00, 0 route DRC,
1 residual antenna violation) is the current best result, kept as-is.
**On resume, if picking this back up: investigate ORFS's antenna-diode
cell/insertion knobs (`ANTENNA_CELL_NAME` or manual `ODB` diode insertion
near net71944-class nets) rather than raising
`MAX_REPAIR_ANTENNAS_ITER_GRT`/`_DRT` again — that lever is exhausted.**
Until then, P4's third size stays documented honestly as "2/3 closed
outright, 3rd routed+timing-closed with 1 known residual antenna violation"
— NOT counted as P4 3/3 closed in ROADMAP.md/README.

## ▶▶ SESSION 8 UPDATE — SUPERSEDED (attempt 2, 2026-07-12 early)

`khnum_sram_1rw_2048x64` (P4, third and last showcase size) attempt 1
finished 2026-07-11 morning: exit 0, GDS produced, but **NOT closed** —
WNS -0.48ns/TNS -0.92ns at 8.0ns, 0 route DRC, but 10 residual antenna
violations (met3/met4 side-area ratio) in final signoff. Diagnosed root
cause: ORFS's antenna-repair loop (`MAX_REPAIR_ANTENNAS_ITER_GRT`/`_DRT`,
default 5 each, undocumented in this repo before now) was still converging
(20→14→10→6 violations) when it hit its default iteration cap.

**Attempt 2 launched same day** (container `sleepy_tharp`, log
`/tmp/harden_2048_attempt2.log`): clock loosened 8.0→8.5ns + both antenna
iteration caps raised (`MAX_REPAIR_ANTENNAS_ITER_GRT=10`,
`MAX_REPAIR_ANTENNAS_ITER_DRT=5`) in
`harden/designs/sky130hd/khnum_sram_1rw_2048x64/{config.mk,constraint.sdc}`.

**Update as of 2026-07-12 ~01:00**: the clock loosening initially backfired
hard (non-monotonic-congestion lesson struck again) — the first full
detail-route pass spiked to **173,341 DRC violations** (vs attempt 1's
peak of ~1,121), a scary ~150x jump. BUT it recovered: iteration-by-
iteration rip-up-reroute drove it to 0 route DRC within ~3 hours
(173,341→50,710→38,372→...→0). Then antenna repair converged cleanly across
rounds: **416→69→4 violations** over 3 repair-reroute cycles (each itself
closing to 0 route DRC). As of the last check, still running — round 4
(for the last 4 antenna violations) has not yet been observed to finish.
Total elapsed so far: ~13 hours (started ~12:23 on 2026-07-11).
**Genuinely promising — likely closes within another 1-3 repair rounds if
the pattern holds, but not yet confirmed closed. Do not assume success
until a future check shows a final `HARDEN_OK` with 0 antenna violations
AND WNS ≥ 0 (timing hasn't been re-checked yet at this clock — that's a
separate thing to verify once routing/antenna fully close).**

**On resume in any future session (context-cleared or new session)**:
1. Check `docker ps -a` for a container still running the harden job, or
   check if `/tmp/harden_2048_attempt2.log` exists and look at its tail —
   note `/tmp/*` does NOT survive a reboot, only survives within this
   machine session.
2. If the container/process is gone and the log doesn't end in `HARDEN_OK`,
   the run was lost (e.g. session/container killed) — just relaunch via
   `bash tools/harden.sh khnum_sram_1rw_2048x64` (config already has the
   attempt-2 settings baked in, no need to redo the tuning).
3. If it DID finish, check for `HARDEN_OK` in the log tail, then check
   `harden/reports/sky130hd/khnum_sram_1rw_2048x64/base/6_finish.rpt` for
   WNS/TNS and `harden/reports/.../grt_antennas.log` for antenna violations
   before declaring P4 closed. Update `harden/HARDEN_RESULTS.md`'s results
   table, this file, `docs/GALLERY.md`, ROADMAP.md, and the
   `project_khnum.md` memory file with the real outcome — do not mark
   closed unless WNS ≥ 0 and 0 antenna violations are both confirmed.

## ▶▶ RESUME HERE (updated 2026-07-10, session 7)

- **Phase:** P4 The Foundry (ASIC hardening) — **2/3 sizes timing-closed, 1/3 open**.
  P5 The Scribe — **3/4 done** (characterization ✅, demo GIF ✅, integration docs ✅;
  gh-pages content pushed, activation deliberately deferred). P3 = ✅ 3/3 (PR #7).
  P2 = ✅ 5/5 (PR #6). P1 = ✅ 7/7 (PRs #2–#4).
- **P3 result: no RTL bug.** `tools/test_fpga.py` runs `synth_xilinx`/`synth_ice40` on
  all 3 SRAM kinds x byte-en on/off at depth 256 and requires real BRAM cells
  (`RAMB18E1`, `SB_RAM40_4K`) in the `stat` tally — **12/12 PASS first try**, zero
  emitter changes needed. Wired into `test_all.py` (skippable via `--quick`).
  **Toolchain gotcha found and worked around**: this machine's `yowasp-yosys` (WASM
  build) silently truncates output mid-ABC-pass during the full `synth_xilinx`/
  `synth_ice40` flow (no error, exit 0, just stops before `stat` prints) — an
  environment quirk, not a Khnum bug. Fix: `-run begin:map_ffram` stops the synth
  flow right after memory-mapping (BRAM techmap already done) and before the broken
  LUT/ABC stage; `stat` there faithfully shows BRAM presence since ABC never touches
  BRAM primitives anyway. Full writeup: `docs/FPGA.md`.
- **P4 progress (this session): `khnum_sram_1rw_256x32` hardened to sky130hd,
  routed GDSII, timing CLOSED (WNS 0.00 ns), 0 routing DRC violations, 374,736 µm²
  @ 43% utilization, peak route RAM 2.11 GB** (well under the 13 GB Docker cap).
  `tools/harden.sh <design>` wraps the OpenROAD-flow-scripts Docker image
  (`--memory=13g --memory-swap=24g` + `LEC_CHECK=0` for the AVX-512 SIGILL gotcha,
  same as KemetCore). Full numbers: `harden/HARDEN_RESULTS.md`. Gallery screenshots
  (ORFS's own auto-generated KLayout renders): `docs/GALLERY.md`.
  **Two real gotchas hit and fixed (both documented in `harden/HARDEN_RESULTS.md`)**:
  (1) ORFS's `SYNTH_MEMORY_MAX_BITS` gate (default 4096 bits) rejects flip-flop
  synthesis of memories bigger than that — raised to 16384 in the design's
  `config.mk` (P4's whole point IS flip-flop hardening of the array, so this is
  the correct fix, not a workaround); (2) `LEC_CHECK=0` needed — this CPU lacks
  AVX-512, same as KemetCore's documented fix.
- **P4 `khnum_sram_1rw_1024x32` — CLOSED after 5 tuning attempts (all same
  session):** (1) 256x32's recipe (`CORE_UTILIZATION=35`/`PLACE_DENSITY=0.55`)
  at 4.0 ns clock — failed global routing outright (`GRT-0232`, met5 ~90%
  congested). (2) `CORE_UTILIZATION=20`/`PLACE_DENSITY=0.45` at 4.0 ns — routed
  clean, but WNS -0.39 ns. (3) same utilization/density at 6.0 ns — WNS
  -0.03 ns, essentially the threshold. (4) same at 6.5 ns — **failed global
  routing again** (`GRT-0232`, met5 ~51%) — the surprising one: clock period
  has a *non-monotonic* effect on routing congestion (a looser timing budget
  changes resizer buffering/upsizing decisions, which changes placement
  density in ways that don't track the period linearly). (5) same at 6.2 ns (a
  smaller step from the known-good 6.0, not another big jump) — **routed clean
  AND closed timing**: WNS 0.00, 0 routing-DRC violations, 0 antenna
  violations, 7.80 GiB peak route RAM. Full iteration history + the
  non-monotonic-congestion lesson: `harden/HARDEN_RESULTS.md`. New screenshots
  in `docs/GALLERY.md` (overwrote the earlier not-closed ones).
- **P4 remaining: 2K×64** — config already prepped and merged
  (`harden/designs/sky130hd/khnum_sram_1rw_2048x64/`, case entry in
  `tools/harden.sh`), starting from a looser recipe than 1024x32's own tuned
  values on both axes (`CORE_UTILIZATION=15`/`PLACE_DENSITY=0.40`, 8.0 ns
  clock) since the previous 4x jump needed loosening both ways. **Not yet
  run.** Given the non-monotonic clock-vs-congestion lesson above: if a step
  fails on congestion, don't just push the period looser — step back and take
  a smaller increment, or address congestion via utilization/density directly.
- **P5 remaining: gh-pages activation** — content is pushed to the `gh-pages`
  branch (a themed single-page HTML site, no external deps) but actually
  **enabling GitHub Pages was deliberately NOT done** — the safety classifier
  correctly flagged it as a public-publish action the user hadn't explicitly
  named, and the same applies to any future attempt: get explicit go-ahead
  first, or the user can just flip it on themselves (repo Settings → Pages →
  source: `gh-pages` branch, root).
- **P6 not started**: PyPI publish and GitHub Release are also public,
  effectively-irreversible-per-version actions — same deliberate deferral
  policy. Don't attempt `twine upload`/`gh release create` without explicit
  user go-ahead even if "keep going" was said broadly; ask specifically for
  this step. Building/checking the package locally (no upload) is fine without
  asking.
- **Next task**: harden 2K×64 (`bash tools/harden.sh khnum_sram_1rw_2048x64`,
  expect 30 min–2+ hours real time per attempt, likely multiple tuning
  attempts per the lessons above). Then P4's stretch items (ASAP7, Liberty/LEF
  stubs) or move to finishing P5 (ask about gh-pages activation) and P6 (ask
  before any actual publish). All per CLAUDE.md.
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
- **Branch state:** `feat/p4-1024x32-timing-closed`, this session — see PR for merge state.

## Honest scoreboard

| Phase | State |
|---|---|
| P0 Genesis | ✅ 8/8 boxes, test-proven |
| P1 Potter's Wheel | ✅ 7/7, test-proven |
| P2 The Proof | ✅ 5/5, test-proven |
| P3 FPGA Gate | ✅ 3/3, test-proven |
| P4 The Foundry | 🔧 3/6, in progress (2/3 sizes timing-closed, 1/3 open) |
| P5 The Scribe | 🔧 3/4 (gh-pages content pushed, activation pending user go-ahead) |
| P6 Ascension | ⬜ 0/5 (PyPI/GitHub Release need explicit user go-ahead before publishing) |

**Total: 29/38 (76%) — "partial" ≠ "done".** (Corrected from a stale 39-box
count carried over several sessions — P0 is actually 8 boxes, not 9; direct
recount via `grep -c` is the source of truth from here on.)

## Session log

- **2026-07-10 (session 7, cont. x3)** — P4 second size CLOSED:
  `khnum_sram_1rw_1024x32` timing closes at 6.2 ns clock (WNS 0.00 ns, 0
  routing-DRC violations, 0 antenna violations, 1,533,880 µm² @ 25% utilization,
  7.80 GiB peak route RAM). Took 5 total tuning attempts across this session
  (see the P4 entry above and `harden/HARDEN_RESULTS.md` for the full
  iteration history). Key new lesson: clock period has a *non-monotonic*
  effect on routing congestion — a 6.5 ns attempt (looser than the
  known-working 6.0 ns) failed global routing on congestion, while the
  smaller 6.2 ns step succeeded. Also shipped this session: `docs/demo.tape`+
  `docs/demo.gif` (VHS terminal demo, house rule), `docs/INTEGRATION.md`,
  `tools/characterize.py` (auto-generates `docs/CHARACTERIZATION.md` from
  harden output — caught and fixed two real accuracy bugs along the way: a
  decimal-GB/binary-GiB unit mixup in hand-written RAM figures, and a
  route-DRC/antenna-violation conflation in the tool's own regex), a README
  accuracy pass, and the `gh-pages` branch content (a themed single-page
  site) pushed but **not activated** — Pages activation and any future PyPI/
  GitHub-Release publish are deliberately deferred pending explicit user
  go-ahead (both flagged by the safety classifier as public-publish actions
  outside the literal scope of "keep going until finish"). 2K×64's recipe is
  prepped and merged but not yet run. Total tracker corrected from a
  long-stale "39 boxes" to the actual 38 (direct recount): 29/38 (76%).
  Also caught and immediately fixed a real mistake this session: a shell
  cwd drift left over from exploring KemetCore's gh-pages branch caused one
  `git checkout -b` to land in the wrong repo — caught before any commit,
  KemetCore fully restored (branch deleted, back on its own main, nothing
  lost). Lesson: always verify `pwd`/`git branch --show-current` before
  committing when multiple repos are in play in the same session.

- **2026-07-10 (session 7, cont. x2)** — P4 second size attempted:
  `khnum_sram_1rw_1024x32`. First attempt (same recipe as 256x32) failed global
  routing outright on congestion (`GRT-0232`, met5 layer ~90% used) — retuned
  `CORE_UTILIZATION` 35→20 and `PLACE_DENSITY` 0.55→0.45, which then routed
  cleanly (0 geometric routing-DRC violations, 1,572,503 µm² @ 25% utilization,
  8.19 GB peak route RAM — well under the 13 GB cap; took ~2h real time end to
  end, including ~7 antenna-repair diode-insertion iterations that converged
  95→1 residual violation rather than fully to 0). **Timing does NOT close**
  at the same 4.0 ns clock as the 256x32 design (WNS -0.39 ns) — 4x the flops
  needs more slack than that budget allows. Recorded honestly as "routed, not
  timing-closed" rather than claimed as a second closed size (scoreboard rule:
  WNS must be ≥ 0). Screenshots + full numbers in `harden/HARDEN_RESULTS.md` /
  `docs/GALLERY.md`. Next-session follow-up: loosen `clk_period` in this
  design's `constraint.sdc` and re-run before starting 2K×64.

- **2026-07-10 (session 7, cont.)** — P4 first size shipped:
  `khnum_sram_1rw_256x32` hardened to sky130hd through `tools/harden.sh`
  (OpenROAD-flow-scripts Docker, mirrors `KemetCore/flow/harden.sh`). Result:
  routed GDSII, timing CLOSED (WNS 0.00 ns, worst slack +0.05 ns), 0 routing DRC
  violations, 374,736 µm² @ 43% utilization, peak route RAM 2.11 GB (well under
  the mandated 13 GB Docker cap — container swap never engaged at this size).
  Hit and fixed two genuine ORFS/environment gotchas (not Khnum RTL bugs):
  `SYNTH_MEMORY_MAX_BITS` (ORFS default 4096 bits refuses flip-flop synthesis
  above that size; raised to 16384 in the design's config.mk — flip-flop
  hardening of the array IS P4's goal) and `LEC_CHECK=0` (this CPU lacks
  AVX-512; ORFS's optional post-resize logical-equivalence check needs an
  AVX-512 binary — identical fix to KemetCore's documented gotcha). Raw ORFS
  output (`harden/{logs,objects,reports,results}/`) gitignored — 28 MB GDS,
  regenerable, matches KemetCore's `flow/` (0 such files tracked in git there
  either); `harden/HARDEN_RESULTS.md` + curated `docs/gallery/*.webp`
  screenshots (ORFS's own auto-generated KLayout renders, copied out via
  `docker run --user $(id -u):$(id -g)` since the container writes as root)
  are the durable, committed evidence. `docs/GALLERY.md` created.

- **2026-07-10 (session 7)** — P3 CLOSED 3/3. Built `tools/test_fpga.py`: runs
  yowasp-yosys `synth_xilinx` and `synth_ice40` on all 3 SRAM kinds x byte-en on/off
  at depth 256, asserts real BRAM cells (`RAMB18E1`, `SB_RAM40_4K`) in the `stat`
  tally via regex on the cell-count lines — 12/12 PASS, zero RTL changes needed
  (Khnum's read-first/sync-read/indexed-part-select emitter style already matches
  both vendors' `memory_libmap` rules). Wired into `test_all.py` (`--quick` skips it,
  same policy as `formal.py`). Found and worked around a real toolchain quirk:
  this machine's `yowasp-yosys` (WASM build) silently truncates output mid-ABC-pass
  during the full `synth_xilinx`/`synth_ice40` flow — exit 0, no error, just stops
  before `stat` ever prints. Diagnosed via `-run <from>:<to>` staged execution:
  `-run begin:map_ffram` stops right after `memory_libmap` + BRAM techmap (confirmed
  present via the `stat` cell tally) and before the broken LUT/ABC stage — sound
  because ABC never touches fixed BRAM primitives. Documented in `docs/FPGA.md`.
  `python3 tools/test_all.py` still ALL GREEN, 185 checks (173 + 12 new), no
  regression.

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
