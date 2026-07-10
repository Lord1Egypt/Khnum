#!/usr/bin/env bash
# Khnum — drive an sky130hd harden (synth->floorplan->place->CTS->route->GDS)
# through the OpenROAD-flow-scripts container. Usage: tools/harden.sh <design>
#
# Mirrors KemetCore's flow/harden.sh pattern (same proven Docker/ORFS recipe),
# renamed flow/ -> harden/ and with an explicit container memory cap: this is a
# 16 GB laptop under WSL2, and OpenROAD detail routing can spike well past a
# container's default cgroup limit. --memory/--memory-swap grants the
# container permission to spill into the VM-wide swap pool instead of getting
# OOM-killed (see CLAUDE.md rule 9 / memory feedback_docker_swap_oom).
#
# LEC_CHECK=0: skip ORFS's post-resize logical-equivalence check -- its bundled
# formal binary (KEPLER_FORMAL_EXE) is compiled with AVX-512 and SIGILLs on
# non-AVX512 CPUs (e.g. this Coffee Lake i7-9750H). The rest of the physical
# flow (synth->place->CTS->route->GDS) is unaffected. Same fix as KemetCore's
# flow/harden.sh (see its FLOW.md).
set -euo pipefail
DESIGN="${1:?usage: tools/harden.sh <design>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${ORFS_IMAGE:-openroad/orfs:latest}"
CFG="/work/harden/designs/sky130hd/${DESIGN}/config.mk"
MAKE_ARGS="${ORFS_MAKE_ARGS:-NUM_CORES=4}"   # cap workers -> bound peak RAM
MEM_ARGS="${DOCKER_MEM_ARGS:---memory=13g --memory-swap=24g}"

case "$DESIGN" in
  khnum_sram_1rw_256x32)
    GEN_ARGS="--kind sram_1rw --depth 256 --width 32" ;;
  khnum_sram_1rw_1024x32)
    GEN_ARGS="--kind sram_1rw --depth 1024 --width 32" ;;
  *)
    echo "tools/harden.sh: unknown design '${DESIGN}' (add its khnum gen flags" \
         "to the case statement above)" >&2
    exit 2 ;;
esac

mkdir -p "${REPO}/harden/rtl"
python3 -m khnum gen ${GEN_ARGS} -o "${REPO}/harden/rtl" --name "${DESIGN}" --no-tb

echo "▶ Hardening '${DESIGN}' on sky130hd via ${IMAGE} (repo ${REPO})"
docker run --rm ${MEM_ARGS} -v "${REPO}:/work" -e LEC_CHECK=0 \
    -w /OpenROAD-flow-scripts/flow "${IMAGE}" \
    bash -lc "source /OpenROAD-flow-scripts/env.sh 2>/dev/null || true;
              make DESIGN_CONFIG=${CFG} WORK_HOME=/work/harden ${MAKE_ARGS} &&
              echo 'HARDEN_OK — GDS under harden/results/'"
