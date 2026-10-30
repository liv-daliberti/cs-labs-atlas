#!/bin/bash
# Discovery crawl for one school into a worker-local capture DB (merged later by merge.py).
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
school=$1
cd /tmp
LPCAP_LOCAL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/disc-$school.sqlite exec ${CS_ATLAS_PY} -I ${CS_ATLAS_HIERARCHY}/labpage-tools-princeton-mit/disc.py $school --threads 10
