# Targeted post-route antenna fix for khnum_sram_1rw_2048x64 (P4, attempt 4).
#
# Attempts 1-3 plateaued at 1 DRT-signoff antenna violation: net71944 into
# output91/A (sky130_fd_sc_hd__clkdlybuf4s50_1), met4 SIDE-area ratio 7646.72
# vs a diode-boosted required 5564.60. Raising MAX_REPAIR_ANTENNAS_ITER_* is a
# spent lever (10->2->1 across cap 5/10/20): each diode iteration reroutes the
# net and the reroute recreates the long met4 segment.
#
# This script instead operates surgically on the finished attempt-3 route
# database (0 route DRC, WNS 0.00 at 8.5ns) via `make run RUN_SCRIPT=...`:
#   1. jumper-only repair first — layer hops split the met4 side area at its
#      source and add no gate load (timing has ZERO margin, diodes add load);
#      critically, NO detailed_route rerun afterwards, so the fix can't be
#      routed away again.
#   2. escalating diode passes (with incremental reroute) only if jumpers
#      alone can't clear it.
# On success the fixed odb overwrites 5_2_route.odb (original backed up), so
# a plain `make` rebuilds only fillcell/6_* — not the ~20h detailed route.

source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_2_route.odb 5_1_grt.sdc

set drt_args [list \
  -output_drc $::env(REPORTS_DIR)/5_route_drc_fix.rpt \
  -output_maze $::env(RESULTS_DIR)/maze_fix.log \
  -drc_report_iter_step 5]

set start_violations [check_antennas]
puts "ANTENNA_FIX: starting with $start_violations violating net(s)"

# Phase 1: jumpers only, escalating aggressiveness. No reroute after these —
# jumper insertion edits the existing wire in place and stays DRC-legal.
foreach margin {10 30 50} {
  if { [check_antennas] == 0 } { break }
  puts "ANTENNA_FIX: repair_antennas -jumper_only -ratio_margin $margin"
  repair_antennas -jumper_only -ratio_margin $margin
}

# Phase 2: diodes as fallback. These DO need an incremental reroute to legally
# connect the diode pin; accept the (small) timing risk only if phase 1 failed.
foreach margin {20 35 50} {
  if { [check_antennas] == 0 } { break }
  puts "ANTENNA_FIX: repair_antennas -ratio_margin $margin (+ incremental reroute)"
  repair_antennas -ratio_margin $margin
  detailed_route {*}$drt_args
}

set remaining [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_fix.log]
if { $remaining > 0 } {
  puts "ANTENNA_FIX_FAIL: $remaining violating net(s) remain after all passes"
  exit 1
}

exec cp $::env(RESULTS_DIR)/5_2_route.odb $::env(RESULTS_DIR)/5_2_route.pre_antenna_fix.odb
orfs_write_db $::env(RESULTS_DIR)/5_2_route.odb
puts "ANTENNA_FIX_OK: 0 antenna violations; fixed odb written to 5_2_route.odb"
exit 0
