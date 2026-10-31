#!/bin/sh
# OpenAlex school sweeps for the PI hierarchy (2026-10-22); one process per school, keys read from the scratchpad env file.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd "$(dirname "$0")/.."
SP=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad
set -a; . $SP/openalex.env; OPENALEX_FLOOR=1500; set +a
for s in "$@"; do nice -n 10 ${CS_ATLAS_PY} -u tools/oa_sweep.py $s > hierarchy/sweep-$s.log 2>&1 & done
wait
