#!/bin/bash
# Wayback history for plan people pages, one shard per process, into worker-local stores (merged later with merge.py).
# The interactive store me-<school>.sqlite is read (not written) so the plan's manual rows resolve.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
school=$1; shard=$2
cd /tmp
LPCAP_EXTRA=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/me-$school.sqlite LPCAP_LOCAL=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lp-local/wb-$school-${shard%/*}.sqlite exec ${CS_ATLAS_PY} -I ${CS_ATLAS_HIERARCHY}/labpage-tools-princeton-mit/wbbatch.py $school --shard $shard
