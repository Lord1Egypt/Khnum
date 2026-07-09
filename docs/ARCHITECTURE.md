# Khnum architecture

## Design philosophy

1. **Text in, text out.** Khnum is a compiler from a tiny config (kind, depth, width,
   options) to Verilog text + JSON manifest. No netlists in memory, no databases —
   generation cost is O(kilobytes) regardless of memory size. This is why a 16 GB
   laptop is enough for everything except P4 place-and-route (which is contained in
   a memory-capped Docker).
2. **Verification artifacts are first-class outputs**, generated from the same config
   in the same call. The TB is not an afterthought — it is the contract.
3. **Portable RTL over PDK bitcells.** Khnum does not craft 6T cells. It emits behavioral
   RTL that (a) infers BRAM on FPGA, (b) hardens to standard-cell RAM via OpenROAD
   (DFFRAM's insight, generalized), (c) can be swapped for a foundry macro at
   integration time using the manifest's port contract.

## Module map

```
khnum/
  __init__.py   version
  __main__.py   python -m khnum
  cli.py        argparse CLI — gen / list; exit 0 ok, 2 config error
  rtl.py        Config (validation) + DUT emitters   <- one function per kind
  tb.py         self-checking TB emitters            <- one function per kind
tools/
  test_all.py   THE gate: CLI hygiene + matrix × (gen, manifest, lint, sim)
tests/          (P2) cocotb suites
docs/           architecture, FPGA/gallery/characterization as phases land
harden/         (P4) ORFS recipes + results
examples/       committed showcase output
```

## Generated-RTL invariants

| invariant | why |
|---|---|
| Verilog-2001 in DUTs | every tool from Icarus to commercial synth accepts it |
| one `always` per memory array | Verilator hard-errors on multi-process memories |
| read-first RDW, documented in header + manifest | the only semantics portable across BRAM and SC-RAM |
| byte writes: `for` + indexed part-select | synthesizes to lane enables, infers BRAM byte-write |
| sync read, 1-cycle latency (except `rf_*_ff`) | matches real SRAM macros, keeps timing honest |
| `-Wall` lint-clean | zero-warning policy catches width bugs at generation time |

## TB architecture (why it's trustworthy)

- Shadow array = independent golden model written in the TB, not derived from the DUT.
- Phase 1 seeds EVERY address (total shadow model — no x-propagation excuses).
- Phase 2 hammers random reads/writes with random byte masks.
- Phase 3 sweeps the full address space again.
- Drive on `negedge`, sample after the following `negedge`: race-free in Verilator
  (--timing), Icarus, and event-driven simulators alike.
- Protocol: exactly one of `KHNUM_TB_PASS` / `KHNUM_TB_FAIL` lines; harness greps both
  (absence of PASS is failure — silent death is caught).

## Manifest contract

`<name>.manifest.json` records kind, geometry, port widths, read latency, RDW
semantics, and the view list. P1 banking adds `children`; P4 adds `gds`/`lef` views.
SoC integrators script against the manifest, never against filename conventions.

## Memory-budget strategy (the 16 GB promise)

- Generation + lint + Verilator sim of the full matrix: < 1 GB.
- cocotb/formal (P2): yowasp-yosys is WASM, bounded by wasm heap; z3 BMC on memories
  this size is < 2 GB.
- ORFS hardening (P4): the only heavy step. Contained in Docker with
  `--memory=13g --memory-swap=24g` (swap absorbs router spikes; WSL2 cap stays
  untouched). Recipes ship with measured peak RSS and are release-gated at 14 GB.
