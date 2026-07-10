"""cocotb suite for sram_1rw — independent Python golden model (not the
Verilog self-checking TB in tests/, and not the formal proof in tools/
formal.py; a third, unrelated verification method over the same RTL).

Semantics under test: read-first RDW, output registered one cycle after ce,
holds its value when ce is low.
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge

DEPTH = int(os.environ.get("DEPTH", "8"))
WIDTH = int(os.environ.get("WIDTH", "16"))
MASK = (1 << WIDTH) - 1


@cocotb.test()
async def test_read_first(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    shadow = [0] * DEPTH
    expected_rdata = 0

    dut.ce.value = 0
    dut.we.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    await RisingEdge(dut.clk)

    random.seed(1)
    ops = [(a, True, True, random.randrange(1 << WIDTH))
           for a in range(DEPTH)]  # directed: write every address once
    for _ in range(2000):
        ops.append((random.randrange(DEPTH), random.random() < 0.85,
                    random.random() < 0.5, random.randrange(1 << WIDTH)))

    for addr, ce, we, wdata in ops:
        pre_val = shadow[addr]
        dut.ce.value = int(ce)
        dut.we.value = int(we)
        dut.addr.value = addr
        dut.wdata.value = wdata
        await RisingEdge(dut.clk)
        await ReadOnly()
        if ce:
            expected_rdata = pre_val
            if we:
                shadow[addr] = wdata & MASK
        got = int(dut.rdata.value)
        assert got == expected_rdata, (
            "rdata mismatch: addr=%d ce=%d we=%d got=%#x exp=%#x"
            % (addr, ce, we, got, expected_rdata))
        await NextTimeStep()  # leave the read-only phase before next iteration's writes

    dut._log.info("KHNUM_COCOTB_PASS")
