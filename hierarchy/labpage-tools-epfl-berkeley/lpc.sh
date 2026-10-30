#!/bin/bash
# usage: lpc.sh ID SCRIPT.py args   -- run a tools script with private capture DBs (scratchpad lpdb/<ID>-<school>.sqlite)
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
W="$1"; shift; SC="$1"; shift
export LPCAP_LOCAL_EPFL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/${W}-epfl.sqlite
export LPCAP_LOCAL_BERKELEY=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb/${W}-berkeley.sqlite
cd /tmp && exec ${CS_ATLAS_PY} -I ${CS_ATLAS_HIERARCHY}/labpage-tools-epfl-berkeley/$SC "$@"
