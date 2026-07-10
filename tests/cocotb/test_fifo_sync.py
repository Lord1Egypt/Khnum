"""cocotb suite for fifo_sync — independent Python golden model (shadow
deque). Checks full/empty/level flags and the FWFT head word every cycle,
including fill-to-full/drain-to-empty and simultaneous push+pop.
"""
import os
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge

DEPTH = int(os.environ.get("DEPTH", "8"))
WIDTH = int(os.environ.get("WIDTH", "16"))
MASK = (1 << WIDTH) - 1


async def _check(dut, q):
    await ReadOnly()
    assert bool(dut.full.value) == (len(q) == DEPTH), "full flag mismatch, level=%d" % len(q)
    assert bool(dut.empty.value) == (len(q) == 0), "empty flag mismatch, level=%d" % len(q)
    assert int(dut.level.value) == len(q), (
        "level mismatch: got=%d exp=%d" % (int(dut.level.value), len(q)))
    if q:
        got = int(dut.rdata.value)
        assert got == q[0], "head mismatch: got=%#x exp=%#x" % (got, q[0])


async def _step(dut, q, push, pop, wdata):
    await _check(dut, q)
    await NextTimeStep()  # leave the read-only phase before driving new stimulus
    dut.push.value = int(push)
    dut.pop.value = int(pop)
    dut.wdata.value = wdata
    was_full, was_empty = len(q) == DEPTH, len(q) == 0
    await RisingEdge(dut.clk)
    dut.push.value = 0
    dut.pop.value = 0
    if push and not was_full:
        q.append(wdata & MASK)
    if pop and not was_empty:
        q.popleft()


@cocotb.test()
async def test_fifo_sync(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    q = deque()
    import random
    random.seed(5)

    dut.rst_n.value = 0
    dut.push.value = 0
    dut.pop.value = 0
    dut.wdata.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    for i in range(DEPTH + 3):  # fill to full, 3 ignored pushes
        await _step(dut, q, True, False, random.randrange(1 << WIDTH))
    for i in range(DEPTH + 3):  # drain to empty, 3 ignored pops
        await _step(dut, q, False, True, 0)
    for i in range(3000):  # random incl. simultaneous push+pop at every occupancy
        r = random.random()
        wdata = random.randrange(1 << WIDTH)
        if r < 0.3:
            await _step(dut, q, True, True, wdata)
        elif r < 0.65:
            await _step(dut, q, True, False, wdata)
        else:
            await _step(dut, q, False, True, 0)
    await _check(dut, q)

    dut._log.info("KHNUM_COCOTB_PASS")
