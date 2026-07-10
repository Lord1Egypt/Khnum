"""cocotb suite for sram_2r1w — independent Python golden model. One write
port + two independent read ports, same clock, read-first RDW on each port.
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
    expected = [0, 0]

    dut.we.value = 0
    dut.waddr.value = 0
    dut.wdata.value = 0
    dut.re0.value = 0
    dut.raddr0.value = 0
    dut.re1.value = 0
    dut.raddr1.value = 0
    await RisingEdge(dut.clk)

    random.seed(3)
    ops = [(a, True, (a + 1) % DEPTH, True, a, True, random.randrange(1 << WIDTH))
           for a in range(DEPTH)]
    for _ in range(2000):
        ops.append((
            random.randrange(DEPTH), random.random() < 0.85,
            random.randrange(DEPTH), random.random() < 0.85,
            random.randrange(DEPTH), random.random() < 0.5,
            random.randrange(1 << WIDTH),
        ))

    for raddr0, re0, raddr1, re1, waddr, we, wdata in ops:
        pre0, pre1 = shadow[raddr0], shadow[raddr1]
        dut.re0.value = int(re0)
        dut.raddr0.value = raddr0
        dut.re1.value = int(re1)
        dut.raddr1.value = raddr1
        dut.we.value = int(we)
        dut.waddr.value = waddr
        dut.wdata.value = wdata
        await RisingEdge(dut.clk)
        await ReadOnly()
        if re0:
            expected[0] = pre0
        if re1:
            expected[1] = pre1
        if we:
            shadow[waddr] = wdata & MASK
        got0, got1 = int(dut.rdata0.value), int(dut.rdata1.value)
        assert got0 == expected[0], "rdata0 mismatch: got=%#x exp=%#x" % (got0, expected[0])
        assert got1 == expected[1], "rdata1 mismatch: got=%#x exp=%#x" % (got1, expected[1])
        await NextTimeStep()  # leave the read-only phase before next iteration's writes

    dut._log.info("KHNUM_COCOTB_PASS")
