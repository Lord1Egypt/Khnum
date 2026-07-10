"""cocotb suite for fifo_async — independent Python golden model. Two
free-running clocks drive the write and read domains; the DUT's CDC (gray
pointers + 2-FF sync) is exercised end-to-end by checking strict FIFO order
between a producer coroutine (wclk) and a consumer coroutine (rclk).
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, NextTimeStep, ReadOnly, RisingEdge, Timer

WIDTH = int(os.environ.get("WIDTH", "16"))
NOPS = 3000
MASK = (1 << WIDTH) - 1


@cocotb.test()
async def test_fifo_async_order(dut):
    cocotb.start_soon(Clock(dut.wclk, 7, units="ns").start())
    cocotb.start_soon(Clock(dut.rclk, 11, units="ns").start())

    dut.wrst_n.value = 0
    dut.rrst_n.value = 0
    dut.push.value = 0
    dut.wdata.value = 0
    dut.pop.value = 0
    await Timer(40, units="ns")
    dut.wrst_n.value = 1
    dut.rrst_n.value = 1

    q = []
    errors = []

    async def producer():
        await RisingEdge(dut.wrst_n)
        i = 0
        while i < NOPS:
            await FallingEdge(dut.wclk)
            await ReadOnly()
            full = bool(dut.full.value)
            await NextTimeStep()  # leave the read-only phase before driving push/wdata
            if not full and (random.randrange(4) != 0):
                wdata = random.randrange(1 << WIDTH)
                q.append(wdata)
                dut.wdata.value = wdata
                dut.push.value = 1
                i += 1
            else:
                dut.push.value = 0
        await FallingEdge(dut.wclk)
        dut.push.value = 0

    async def consumer():
        await RisingEdge(dut.rrst_n)
        i = 0
        while i < NOPS:
            await FallingEdge(dut.rclk)
            await ReadOnly()
            empty = bool(dut.empty.value)
            await NextTimeStep()  # leave the read-only phase before driving pop
            if not empty and (random.randrange(4) != 0):
                got = int(dut.rdata.value)
                exp = q[i]
                if got != exp:
                    errors.append("order idx=%d got=%#x exp=%#x" % (i, got, exp))
                dut.pop.value = 1
                i += 1
            else:
                dut.pop.value = 0
        await FallingEdge(dut.rclk)
        dut.pop.value = 0

    random.seed(6)
    prod = cocotb.start_soon(producer())
    cons = cocotb.start_soon(consumer())
    await prod
    await cons

    assert not errors, "\n".join(errors[:20])
    dut._log.info("KHNUM_COCOTB_PASS")
