export DESIGN_NAME     = khnum_sram_1rw_1024x32
export PLATFORM         = sky130hd

export VERILOG_FILES    = /work/harden/rtl/khnum_sram_1rw_1024x32.v
export SDC_FILE         = $(dir $(DESIGN_CONFIG))/constraint.sdc

# Register-array-dominated design (1024x32 = 32768 flops + read-first mux/decode).
# First attempt at CORE_UTILIZATION=35/PLACE_DENSITY=0.55 (the 256x32 recipe)
# failed global routing on met5 congestion (~90% usage, GRT-0232) -- 4x the
# flops in the same relative density leaves the router too little slack.
# Lower utilization/density to give it room; this is exactly the "retune before
# scaling further" step CLAUDE.md/ROADMAP anticipate.
export CORE_UTILIZATION  = 20
export PLACE_DENSITY     = 0.45
export CORE_ASPECT_RATIO = 1

# See khnum_sram_1rw_256x32/config.mk for why this is raised (ORFS's default
# 4096-bit gate refuses flip-flop synthesis above that size; flip-flop
# hardening of the array IS P4's goal). This design is 32768 bits.
export SYNTH_MEMORY_MAX_BITS = 65536
