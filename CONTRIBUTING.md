# Contributing to Khnum

Khnum welcomes contributions — the bar is simple and non-negotiable:

1. **Zero dependencies.** The `khnum/` package imports Python 3 stdlib only.
2. **The gate.** `python3 tools/test_all.py` must exit 0. New features need new
   matrix entries covering them. You'll need `verilator` installed (`apt install verilator`).
3. **Lint-clean DUTs.** Generated RTL passes `verilator --lint-only -Wall` with zero
   warnings. Testbench code may warn; DUT code may not.
4. **Honest docs.** If your PR ships a feature, move it from "roadmap" to "shipped" in
   README/ROADMAP in the same PR — and never the other way around.
5. **PRs only.** Branch from `main`, open a PR, keep it focused. Direct pushes to main
   are disabled by convention.

## Development quickstart

```bash
git clone https://github.com/Lord1Egypt/Khnum && cd Khnum
python3 -m khnum list
python3 tools/test_all.py   # must print ALL GREEN before and after your change
```

## Generated-RTL rules

Read the docstring at the top of `khnum/rtl.py` and `docs/ARCHITECTURE.md` before
touching emitters. Key traps:

- One `always` block per memory array (Verilator rejects multi-driven memories).
- Read-first RDW semantics everywhere (portability contract).
- Emitters use Python `%`-formatting: literal `%` in Verilog must be `%%`.
- Verilog-2001 only in DUT code; SystemVerilog only under `` `ifdef FORMAL ``.

## Reporting bugs

Open an issue with the exact `python3 -m khnum gen ...` command, your Verilator
version, and the failing output. A failing config we can reproduce becomes a
regression matrix entry — the best kind of bug report.
