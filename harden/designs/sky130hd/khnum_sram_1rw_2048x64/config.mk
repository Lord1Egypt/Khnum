export DESIGN_NAME     = khnum_sram_1rw_2048x64
export PLATFORM         = sky130hd

export VERILOG_FILES    = /work/harden/rtl/khnum_sram_1rw_2048x64.v
export SDC_FILE         = $(dir $(DESIGN_CONFIG))/constraint.sdc

# Register-array-dominated design (2048x64 = 131072 flops + read-first mux/decode)
# -- 4x the flops of khnum_sram_1rw_1024x32 again. Starting from that design's
# retuned recipe (CORE_UTILIZATION=20/PLACE_DENSITY=0.45 fixed a routing-
# congestion failure there) rather than the original 256x32 recipe, since a
# bigger register array needs at least as much routing headroom, likely more.
export CORE_UTILIZATION  = 15
export PLACE_DENSITY     = 0.40
export CORE_ASPECT_RATIO = 1

# See khnum_sram_1rw_256x32/config.mk for why this is raised (ORFS's default
# 4096-bit gate refuses flip-flop synthesis above that size; flip-flop
# hardening of the array IS P4's goal). This design is 131072 bits.
export SYNTH_MEMORY_MAX_BITS = 262144
