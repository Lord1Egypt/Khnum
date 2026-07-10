"""cocotb suite for sram_1r1w — independent Python golden model. Separate
write port (we/waddr/wdata) and read port (re/raddr), same clock, read-first
RDW: a read of an address being written in the same cycle sees the old data.
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

    dut.we.value = 0
    dut.waddr.value = 0
    dut.wdata.value = 0
    dut.re.value = 0
    dut.raddr.value = 0
    await RisingEdge(dut.clk)

    random.seed(2)
    ops = [(a, True, a, True, random.randrange(1 << WIDTH)) for a in range(DEPTH)]
    for _ in range(2000):
        ops.append((
            random.randrange(DEPTH), random.random() < 0.5,
            random.randrange(DEPTH), random.random() < 0.85,
            random.randrange(1 << WIDTH),
        ))

    for raddr, re, waddr, we, wdata in ops:
        pre_val = shadow[raddr]
        dut.re.value = int(re)
        dut.raddr.value = raddr
        dut.we.value = int(we)
        dut.waddr.value = waddr
        dut.wdata.value = wdata
        await RisingEdge(dut.clk)
        await ReadOnly()
        if re:
            expected_rdata = pre_val
        if we:
            shadow[waddr] = wdata & MASK
        got = int(dut.rdata.value)
        assert got == expected_rdata, (
            "rdata mismatch: raddr=%d re=%d got=%#x exp=%#x"
            % (raddr, re, got, expected_rdata))
        await NextTimeStep()  # leave the read-only phase before next iteration's writes

    dut._log.info("KHNUM_COCOTB_PASS")
