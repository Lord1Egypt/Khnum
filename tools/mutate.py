#!/usr/bin/env python3
"""Mutation operators for Khnum's formal proofs.

A formal proof that survives a deliberately-broken design is decoration
(KemetCore shipped 8 such fake proofs before this rule existed). For each
SRAM kind we define ONE semantic mutation that breaks read-during-write
semantics — turning read-first into write-through. `tools/formal.py` applies
it and REQUIRES the proof to fail; if the "broken" design still verifies, the
property is vacuous and the run fails.

The mutation is a single, exact source substitution against the emitter's
output. `mutate()` asserts it actually changed the text, so if an emitter is
ever refactored the mutation loudly breaks instead of silently no-op'ing.
"""

# kind -> (exact substring in generated RTL, read-first-violating replacement)
MUTATIONS = {
    "sram_1rw": (
        "rdata <= mem[addr];",
        "rdata <= we ? wdata : mem[addr];",
    ),
    "sram_1r1w": (
        "if (re) rdata <= mem[raddr];",
        "if (re) rdata <= (we && waddr==raddr) ? wdata : mem[raddr];",
    ),
    "sram_2r1w": (
        "if (re0) rdata0 <= mem[raddr0];",
        "if (re0) rdata0 <= (we && waddr==raddr0) ? wdata : mem[raddr0];",
    ),
}


def mutate(text, kind):
    """Return `text` with its read-first behavior broken. Raises if the kind
    has no mutation or the target substring is absent (emitter drifted)."""
    if kind not in MUTATIONS:
        raise ValueError("no mutation defined for kind %r" % kind)
    old, new = MUTATIONS[kind]
    if text.count(old) != 1:
        raise ValueError("mutation target for %s not found exactly once "
                         "(found %d) — emitter drifted?" % (kind, text.count(old)))
    return text.replace(old, new)
