# cocotb + Verilator suites for Khnum — one per generated kind.
#   make CORE=sram_1rw    (default)
#   make CORE=sram_1r1w
#   make CORE=sram_2r1w
#   make CORE=rf_2r1w_ff
#   make CORE=fifo_sync
#   make CORE=fifo_async
#
# Each target generates a fresh DUT (module name fixed to "dut" via --name so
# VERILOG_SOURCES/TOPLEVEL stay static) into gen/$(CORE)/dut.v, then drives it
# with an independent Python golden model — a second, unrelated verification
# method from the Verilog self-checking TB (tests/) and the formal proofs
# (tools/formal.py). DEPTH/WIDTH are exported so the test module can size its
# shadow model identically.
TOPLEVEL_LANG = verilog
SIM ?= verilator
CORE ?= sram_1rw
PWD := $(shell pwd)
ROOT := $(abspath $(PWD)/../..)
GEN := $(PWD)/gen/$(CORE)

export DEPTH ?= 8
export WIDTH ?= 16

# Eager (parse-time) generation: VERILOG_SOURCES below must exist before any
# cocotb/Makefile.sim target runs, so we shell out here rather than as a
# make-target dependency.
_GEN_OUT := $(shell mkdir -p $(GEN) && cd $(ROOT) && python3 -m khnum gen \
  --kind $(CORE) --depth $(DEPTH) --width $(WIDTH) --name dut --no-tb -o $(GEN) 2>&1)
ifeq ($(findstring khnum: error,$(_GEN_OUT)),khnum: error)
$(error khnum gen failed: $(_GEN_OUT))
endif

VERILOG_SOURCES = $(GEN)/dut.v
TOPLEVEL = dut
MODULE = test_$(CORE)
SIM_BUILD = sim_build_$(CORE)
EXTRA_ARGS += --no-timing

include $(shell cocotb-config --makefiles)/Makefile.sim
