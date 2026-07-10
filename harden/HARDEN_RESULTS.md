# Khnum — ASIC hardening results (P4 — The Foundry)

Signed-off sky130hd (open-source SkyWater 130nm) layouts, produced locally via
`tools/harden.sh` through the OpenROAD-flow-scripts Docker image (same proven
recipe as KemetCore's `flow/harden.sh`). WNS ≥ 0 ⇒ timing closes at the clock
in each design's `constraint.sdc`.

Raw ORFS output (`harden/{logs,objects,reports,results}/`) is gitignored —
multi-GB scale and fully regenerable via `tools/harden.sh <design>` — mirroring
KemetCore's `flow/` (0 GDS/log/object files tracked in git there either).
This file + the curated screenshots in `docs/gallery/` are the durable record.

| design | platform | GDS | area (µm²) | util | clock period (ns) | WNS (ns) | route DRC | peak route RAM | closes |
|--------|----------|----:|-----------:|:----:|-------------------:|---------:|:---------:|----------------:|:------:|
| `khnum_sram_1rw_256x32` | sky130hd | 28 MB | 374,736 | 43% | 4.0 | 0.00 (worst slack +0.05) | 0 viol | 2.17 GB | ✅ |
| `khnum_sram_1rw_1024x32` | sky130hd | 155 MB | 1,572,503 | 25% | 4.0 | **-0.39** | 0 viol (1 residual antenna) | 8.19 GB | ❌ **not yet** |

`khnum_sram_1rw_1024x32` routes cleanly (0 geometric routing-DRC violations,
still comfortably under the 13 GB RAM cap) but **does not close timing** at the
same 4.0 ns clock used for the smaller design — WNS -0.39 ns. This is an
honest, expected result, not a bug: 4x the flops means 4x the clock-tree
insertion delay and mux/decode fan-in, so the same period is simply too
aggressive at this size. **Not being reported as a closed size** — per this
file's own convention (WNS ≥ 0 ⇒ closes), and ROADMAP.md's "partial is not
done" rule. Fix for next session: loosen `clk_period` in this design's
`constraint.sdc` (e.g. to 6.0-8.0 ns) and re-run; the routed geometry itself is
sound, so this should just need the timing target relaxed, not a placement/
routing retune. One residual antenna violation also remains after the
repair loop's diode-insertion rounds converged to 1 rather than 0 (down from
95 initially) — worth re-checking once the clock period is fixed, but is a
separate, lower-priority item (antenna violations are a reliability/yield
concern, not a functional-correctness one, and diode insertion is best-effort
in ORFS, not guaranteed to reach exactly 0).

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
during the heaviest stage (detail routing, `5_2_route.log`) was **2.17 GB** —
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
  that closes at one size is not guaranteed to close at 4x the flops — see the
  `khnum_sram_1rw_1024x32` WNS -0.39 ns result above. Each new size's
  `constraint.sdc` needs its own timing budget, sized for its own datapath.

## Next sizes

Per ROADMAP.md P4: 2Kx64 remains. `khnum_sram_1rw_1024x32` needs a follow-up
run with a looser clock period (see above) before it can be marked closed.
Watch `SYNTH_MEMORY_MAX_BITS`, routing congestion (retune utilization/density
if `GRT-0232` appears), and peak route RAM per size — recipes that exceed
~13 GB peak need retuning before going bigger, per the 16 GB laptop
constraint (1024x32 at 8.19 GB shows there's still headroom before 2Kx64).
