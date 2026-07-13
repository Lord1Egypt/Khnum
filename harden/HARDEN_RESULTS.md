# Khnum — ASIC hardening results (P4 — The Foundry)

Signed-off sky130hd (open-source SkyWater 130nm) layouts, produced locally via
`tools/harden.sh` through the OpenROAD-flow-scripts Docker image (same proven
recipe as KemetCore's `flow/harden.sh`). WNS ≥ 0 ⇒ timing closes at the clock
in each design's `constraint.sdc`.

Raw ORFS output (`harden/{logs,objects,reports,results}/`) is gitignored —
multi-GB scale and fully regenerable via `tools/harden.sh <design>` — mirroring
KemetCore's `flow/` (0 GDS/log/object files tracked in git there either).
This file + the curated screenshots in `docs/gallery/` are the durable record.
This table is now maintained by `tools/characterize.py` (`docs/CHARACTERIZATION.md`
is its auto-generated output) — regenerate rather than hand-edit numbers.
**RAM figures are GiB** (KB/1024/1024, matching `free`/`docker stats`), not
decimal GB — an earlier draft of this file mixed the two and slightly
overstated a couple of entries; fixed once `tools/characterize.py` existed to
compute them consistently.

| design | platform | GDS | area (µm²) | util | clock period (ns) | WNS (ns) | route DRC | antenna | peak route RAM | closes |
|--------|----------|----:|-----------:|:----:|-------------------:|---------:|:---------:|--------:|----------------:|:------:|
| `khnum_sram_1rw_256x32` | sky130hd | 28 MB | 374,736 | 43% | 4.0 | 0.00 (worst slack +0.05) | 0 viol | 0 | 2.11 GB | ✅ |
| `khnum_sram_1rw_1024x32` | sky130hd | 154 MB | 1,533,880 | 25% | 6.2 | 0.00 | 0 viol | 0 | 7.80 GB | ✅ |

`khnum_sram_1rw_1024x32` took **5 attempts** to close, all real signal, no
dead ends papered over:
1. `CORE_UTILIZATION=35`/`PLACE_DENSITY=0.55` (256x32's recipe) at 4.0 ns —
   failed global routing outright (`GRT-0232`, met5 ~90% congested).
2. `CORE_UTILIZATION=20`/`PLACE_DENSITY=0.45` at 4.0 ns — routed cleanly, but
   WNS -0.39 ns (too aggressive a clock for 4x the flops).
3. Same utilization/density at 6.0 ns — WNS -0.03 ns, essentially the
   threshold, routed clean (0 DRC, 1 residual antenna).
4. Same utilization/density at 6.5 ns — **failed global routing again**
   (`GRT-0232`, met5 ~51%). This was the surprising one: clock period has a
   *non-monotonic* effect on congestion here, because a looser timing budget
   changes how hard the resizer buffers/upsizes cells, which changes local
   cell density in ways that don't simply track the period. A "just add more
   margin" instinct is not safe with this knob.
5. Same utilization/density at 6.2 ns (a smaller step from the known-good 6.0)
   — **routed clean AND closed timing**: WNS 0.00, 0 routing-DRC violations,
   0 antenna violations, 7.80 GiB peak route RAM.

Lesson for the next size (2Kx64) and beyond: when a clock-period bump fails on
*routing congestion* rather than timing, don't keep pushing the period up —
step back down and take a smaller increment, or address congestion directly
via utilization/density instead. The two knobs (timing budget, placement
density) interact and neither is a strictly safe direction to push
independently.

## How this was produced

```bash
tools/harden.sh khnum_sram_1rw_256x32
```

Runs inside `openroad/orfs:latest` with `--memory=13g --memory-swap=24g`
(container-level RAM+swap grant — see CLAUDE.md rule 9 /
[[feedback-docker-swap-oom]]) and `LEC_CHECK=0` (skips ORFS's optional
post-resize logical-equivalence check, whose bundled formal binary is
AVX-512-only and SIGILLs on this machine's Coffee Lake CPU — same fix as
KemetCore's `flow/harden.sh`, see its `FLOW.md`). Peak RAM actually used
during the heaviest stage (detail routing, `5_2_route.log`) was **2.11 GB** —
comfortably inside the 13 GB cap; container swap was never engaged for this
design size.

## Gotchas hit this session (both genuine ORFS behavior, not Khnum RTL bugs)

- **`SYNTH_MEMORY_MAX_BITS`** (ORFS default: 4096 bits) rejects synthesizing a
  Yosys-inferred memory into flip-flops above that size — it expects a real RAM
  macro/fakeram for anything bigger, since flip-flop RAM is usually a mistake
  at scale. Khnum's P4 goal is exactly DFFRAM-style flip-flop hardening of the
  array, so `harden/designs/sky130hd/khnum_sram_1rw_256x32/config.mk` raises it
  to 16384 (this design is 8192 bits) with headroom for the next size.
- **`LEC_CHECK=0`** — see above; identical root cause and fix to KemetCore's
  documented AVX-512 gotcha.
- **Global-routing congestion at higher utilization**: `khnum_sram_1rw_1024x32`'s
  first attempt (same `CORE_UTILIZATION=35`/`PLACE_DENSITY=0.55` as the 256x32
  recipe) failed global routing outright (`GRT-0232`, met5 layer ~90% congested)
  — 4x the flops in the same relative density leaves the router no slack.
  Fixed by lowering to `CORE_UTILIZATION=20`/`PLACE_DENSITY=0.45` (more die
  area per cell), which routed cleanly. Confirms CLAUDE.md's existing guidance
  ("if detail route OOMs, reduce CORE_UTILIZATION / increase die area") applies
  to routing-congestion failures too, not just OOM.
- **Timing does not automatically carry over between sizes**: a clock period
  that closes at one size is not guaranteed to close at 4x the flops. Each new
  size's `constraint.sdc` needs its own timing budget, sized for its own
  datapath.
- **Clock period vs. routing congestion is non-monotonic**: `khnum_sram_1rw_1024x32`
  routed cleanly at 6.0 ns, then FAILED global routing at 6.5 ns (a looser
  clock, which should intuitively be "easier"), then routed and closed cleanly
  at 6.2 ns. A looser timing budget changes the resizer's buffering/upsizing
  decisions, which changes local placement density in ways that don't track
  linearly with the period. Take small steps when hunting for a closing clock
  period, and if a step fails on congestion (not timing), don't assume a
  bigger step will fix it — it may make congestion worse, not better.

## Next sizes

Per ROADMAP.md P4: 2Kx64 remains, **routed and timing-closed but not fully
antenna-clean — 1 known residual violation after 3 tuning attempts,
plateaued (see table + writeup below); paused rather than continuing to
raise iteration caps**. Watch
`SYNTH_MEMORY_MAX_BITS`, routing congestion (retune utilization/density if
`GRT-0232` appears, and prefer small clock-period steps per the lesson
above), and peak route RAM per size — recipes that exceed ~13 GB peak need
retuning before going bigger, per the 16 GB laptop constraint (1024x32 at
7.80 GiB shows there's still headroom before 2Kx64, though 2Kx64's starting
recipe already uses a lower utilization/looser clock than 1024x32's as a
precaution).

`khnum_sram_1rw_2048x64` attempt 1 (`CORE_UTILIZATION=15`/`PLACE_DENSITY=0.40`,
8.0 ns, ~18.3h wall time): **finished (exit 0, GDS produced) but NOT closed.**
- Timing: WNS -0.48 ns, TNS -0.92 ns at 8.0 ns — clock too tight for this
  design's datapath, same "each size needs its own budget" lesson as 1024x32.
- Routing DRC: 0 violations (clean) — congestion is not the blocker here,
  unlike 1024x32's saga.
- Antenna: final signoff (`grt_antennas.log`, post-fill GDS-level check) found
  **10 residual violations**, all met3/met4 side-area-ratio overages. During
  the run itself, the routing-time antenna-repair loop visibly converged each
  round (20 → 14 → 10 → 6 violations across successive
  `Complete detail routing` cycles) — still trending down, not plateaued, when
  it hit ORFS's default iteration cap (`MAX_REPAIR_ANTENNAS_ITER_GRT`/`_DRT`,
  default 5 each, found in `flow/scripts/variables.yaml` inside the
  `openroad/orfs` image — undocumented in this repo until now). Peak route RAM
  ~12.06 GB (`5_2_route.odb` in the per-stage timing table), comfortably under
  the 13 GB cap.

Attempt 2 (`clk_period` 8.0 → 8.5 ns,
`MAX_REPAIR_ANTENNAS_ITER_GRT=10`/`MAX_REPAIR_ANTENNAS_ITER_DRT=5`, ~19h wall
time): **finished (exit 0, `HARDEN_OK`, GDS produced) — close but still NOT
closed.**
- Routing DRC: 0 violations (clean) — the mid-run 150x DRC spike from the
  clock change (173,341 violations on the first detail-route pass) fully
  recovered via rip-up-reroute within ~3h; non-monotonic-congestion lesson
  held (see above) but didn't block closure this time.
- Timing: WNS 0.00 ns, TNS 0.00 ns, worst slack +0.32 ns at 8.5 ns —
  genuinely closed.
- Antenna: **still 1 residual violation** in both `grt_antennas.log` and
  `drt_antennas.log` signoff (met4 side-area ratio, required 6959.96 vs
  actual 9127.44), despite the repair loop converging the mid-run count all
  the way down (416 → 69 → 4 → 1 across repair-reroute rounds) — doubling
  the iteration cap got very close but not to 0.

Attempt 3 (caps raised further to `MAX_REPAIR_ANTENNAS_ITER_GRT=20`/
`MAX_REPAIR_ANTENNAS_ITER_DRT=10`, clock left at 8.5 ns, ~24h wall time):
**finished (exit 0, `HARDEN_OK`, GDS produced) — same plateau.**
- Routing DRC: 0 violations (clean).
- Timing: WNS 0.00 ns, TNS 0.00 ns, worst slack +0.40 ns — closed, slightly
  better margin than attempt 2.
- Antenna: `grt_antennas.log` now clean (0 violations, improved from
  attempt 2's 1) but `drt_antennas.log` signoff still shows **1 residual
  violation** (met4 side-area ratio, required 5564.60 vs actual 7646.72,
  on a different net than attempt 2's but the same profile — a
  `clkdlybuf4s50`-driven high-fanout clock-buffer net).

**Summary across all 3 attempts**: antenna cap 5→10→20 drove signoff
violations 10 → 2 (1 grt + 1 drt) → 1 (drt only) — real but sharply
diminishing progress. This looks like a genuine ceiling for cap-bumping
alone: the same class of net (clock-buffer output, inherently high
fanout/wire area) keeps landing just over the antenna ratio no matter how
many repair rounds are allowed. **Decision: pause here rather than launch a
4th multi-hour attempt with an even higher cap** — the next productive
lever is a targeted one (antenna diode cell sizing/insertion near that
specific net class, or CTS-level buffering/net splitting), not another
blind iteration-cap increase. `khnum_sram_1rw_2048x64` is therefore
**documented as: routed, timing-closed, 1 known residual antenna
violation** — not counted as a fully clean P4 close until that specific
lever is tried.
