"""cocotb suite for rf_2r1w_ff — independent Python golden model. One
synchronous write port + two asynchronous (combinational) read ports: rdata
tracks mem[raddr] with zero latency, including during the same cycle a write
lands (the write only becomes visible on rdata AFTER the clock edge, since the
write itself is registered).
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge, Timer

DEPTH = int(os.environ.get("DEPTH", "8"))
WIDTH = int(os.environ.get("WIDTH", "16"))
MASK = (1 << WIDTH) - 1


async def _check_async_reads(dut, shadow):
    await ReadOnly()
    got0 = int(dut.rdata0.value)
    got1 = int(dut.rdata1.value)
    exp0 = shadow[int(dut.raddr0.value)]
    exp1 = shadow[int(dut.raddr1.value)]
    assert got0 == exp0, "rdata0 mismatch: got=%#x exp=%#x" % (got0, exp0)
    assert got1 == exp1, "rdata1 mismatch: got=%#x exp=%#x" % (got1, exp1)


@cocotb.test()
async def test_async_read_and_write(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    shadow = [0] * DEPTH

    dut.we.value = 0
    dut.waddr.value = 0
    dut.wdata.value = 0
    dut.raddr0.value = 0
    dut.raddr1.value = 0
    await RisingEdge(dut.clk)
    await _check_async_reads(dut, shadow)
    await NextTimeStep()  # leave the read-only phase before the loop's first writes

    random.seed(4)
    ops = [(a, True, wdata) for a, wdata in
           ((a, random.randrange(1 << WIDTH)) for a in range(DEPTH))]
    for _ in range(2000):
        ops.append((random.randrange(DEPTH), random.random() < 0.5,
                    random.randrange(1 << WIDTH)))

    for waddr, we, wdata in ops:
        dut.we.value = int(we)
        dut.waddr.value = waddr
        dut.wdata.value = wdata
        dut.raddr0.value = random.randrange(DEPTH)
        dut.raddr1.value = random.randrange(DEPTH)
        # async reads must reflect shadow state BEFORE this write settles
        await _check_async_reads(dut, shadow)
        await RisingEdge(dut.clk)
        if we:
            shadow[waddr] = wdata & MASK
        await Timer(1, units="ns")  # let combinational reads settle post-edge
        await _check_async_reads(dut, shadow)
        await NextTimeStep()  # leave the read-only phase before next iteration's writes

    dut._log.info("KHNUM_COCOTB_PASS")
