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

## Next sizes

Per ROADMAP.md P4: scale up (e.g. 1Kx32, 2Kx64) once the base recipe is
proven, watching `SYNTH_MEMORY_MAX_BITS` and peak route RAM per size — recipes
that exceed ~13 GB peak need retuning (lower `CORE_UTILIZATION` / larger die)
before going bigger, per the 16 GB laptop constraint.
