# Targeted post-route antenna fix for khnum_sram_1rw_2048x64 — v2 (P4, attempt 5).
#
# v1 (fix_antenna.tcl) taught two things, measured on this exact database:
#   * jumper-only repair cannot touch the pathological net (net71944, met4
#     side-area 7646.72 vs diode-boosted required 5564.60): three passes at
#     margins 10/30/50 inserted nothing usable — no legal layer hop there.
#   * ESCALATING margins diverge: margin 20/35/50 diode passes went
#     1 -> 61 -> 61 -> 89 violations, because a bigger margin widens the rip
#     scope (848 -> ~1400 -> ~3400 nets) and each bigger incremental reroute
#     mints more new marginal violations than the pass fixes.
#
# Why attempt 3's bare loop plateaued at 1: repair sizes diodes for the wire
# it SEES, then the post-repair reroute grew that wire ~37% (required 5564 vs
# final partial 7646) — protection is always one reroute behind. So:
#
#   Pass 1: single margin-40 overshoot pass (> the observed 37% growth) to
#           protect net71944 and everything near the limit in one shot.
#   Cleanup: bare (margin-0) passes ONLY — minimal rip scope, the regime
#           where the flow's own loop converged 416 -> 69 -> 4. Before each
#           diode pass, try a free bare jumper-only pass (no reroute, zero
#           churn). Stop early on plateau instead of burning ~1h reroutes.
#
# Nothing is written to disk unless the final check is 0 violations.

source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_2_route.odb 5_1_grt.sdc

set drt_args [list \
  -output_drc $::env(REPORTS_DIR)/5_route_drc_fix2.rpt \
  -output_maze $::env(RESULTS_DIR)/maze_fix2.log \
  -drc_report_iter_step 5]

puts "ANTENNA_FIX2: starting with [check_antennas] violating net(s)"

puts "ANTENNA_FIX2: pass 1 — repair_antennas -ratio_margin 40 (+ incremental reroute)"
repair_antennas -ratio_margin 40
detailed_route {*}$drt_args

set prev -1
for { set i 1 } { $i <= 6 } { incr i } {
  set n [check_antennas]
  puts "ANTENNA_FIX2: cleanup iter $i starts at $n violating net(s)"
  if { $n == 0 } { break }
  if { $prev >= 0 && $n >= $prev } {
    puts "ANTENNA_FIX2: plateau ($prev -> $n), stopping early"
    break
  }
  set prev $n
  # Free attempt first: bare jumper-only, no reroute, cannot mint churn.
  repair_antennas -jumper_only
  if { [check_antennas] == 0 } { break }
  puts "ANTENNA_FIX2: cleanup iter $i — bare repair_antennas (+ incremental reroute)"
  repair_antennas
  detailed_route {*}$drt_args
}

set remaining [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_fix2.log]
if { $remaining > 0 } {
  puts "ANTENNA_FIX2_FAIL: $remaining violating net(s) remain"
  exit 1
}

exec cp $::env(RESULTS_DIR)/5_2_route.odb $::env(RESULTS_DIR)/5_2_route.pre_antenna_fix.odb
orfs_write_db $::env(RESULTS_DIR)/5_2_route.odb
puts "ANTENNA_FIX2_OK: 0 antenna violations; fixed odb written to 5_2_route.odb"
exit 0
