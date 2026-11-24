#!/bin/sh
set -a; . /tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/openalex.env; set +a
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
cd ${CS_ATLAS_HIERARCHY}/gap-tools-cmu
for a in "$@"; do echo "######## $a"; ${CS_ATLAS_PY} -I oa.py works $a --n 40; done
