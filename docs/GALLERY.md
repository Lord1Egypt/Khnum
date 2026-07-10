# GDS Gallery

Routed layouts from `tools/harden.sh` (OpenROAD/ORFS, sky130hd). Screenshots are
ORFS's own auto-generated KLayout renders (`harden/reports/.../final_*.webp`),
copied here since the raw GDS/logs/reports tree is gitignored (regenerable,
multi-GB scale — see `harden/HARDEN_RESULTS.md`).

## `khnum_sram_1rw_256x32` — sky130hd

256 x 32 single-port SRAM (read-first), hardened to standard-cell flip-flop RAM
(DFFRAM-style). 374,736 µm², 43% utilization, timing closes at 4.0 ns (WNS
0.00 ns), 0 routing DRC violations. Full numbers: `harden/HARDEN_RESULTS.md`.

### Full routed layout

![khnum_sram_1rw_256x32 routed layout](gallery/khnum_sram_1rw_256x32_sky130hd.webp)

### Routing detail

![khnum_sram_1rw_256x32 routing](gallery/khnum_sram_1rw_256x32_sky130hd_routing.webp)

## `khnum_sram_1rw_1024x32` — sky130hd

1024 x 32 single-port SRAM, hardened to standard-cell flip-flop RAM. Routes
cleanly (0 geometric routing-DRC violations) at 1,572,503 µm², 25%
utilization, but **timing does not yet close** at the 4.0 ns clock used here
(WNS -0.39 ns) — a looser clock period is the fix, tracked as a follow-up in
`harden/HARDEN_RESULTS.md`. Shown here to be transparent about where the
recipe currently stands, not just the wins.

### Full routed layout

![khnum_sram_1rw_1024x32 routed layout](gallery/khnum_sram_1rw_1024x32_sky130hd.webp)

### Routing detail

![khnum_sram_1rw_1024x32 routing](gallery/khnum_sram_1rw_1024x32_sky130hd_routing.webp)
