export DESIGN_NAME     = khnum_sram_1rw_256x32
export PLATFORM         = sky130hd

export VERILOG_FILES    = /work/harden/rtl/khnum_sram_1rw_256x32.v
export SDC_FILE         = $(dir $(DESIGN_CONFIG))/constraint.sdc

# Register-array-dominated design (256x32 = 8192 flops + read-first mux/decode),
# same order of magnitude as KemetCore's flop register files -> same starting
# utilization/density (see KemetCore/flow/designs/asap7/seth_regfile/config.mk).
export CORE_UTILIZATION  = 35
export PLACE_DENSITY     = 0.55
export CORE_ASPECT_RATIO = 1

# ORFS's default memory-synthesis gate (SYNTH_MEMORY_MAX_BITS=4096) refuses to
# turn a Yosys-inferred memory into flip-flops above that size -- it expects
# real RAM macros/fakeram for anything bigger. Khnum's whole P4 point IS
# genuine DFFRAM-style standard-cell flip-flop hardening of the array, so
# raise the ceiling to fit this design (256*32 = 8192 bits) with headroom.
export SYNTH_MEMORY_MAX_BITS = 16384
