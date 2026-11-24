#!/bin/bash
# Wayback captures of each lab's main people page (autospec.py wayback), 2 shards per school, local DBs.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
T=${CS_ATLAS_HIERARCHY}/labpage-tools-epfl-berkeley
S=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb
for school in epfl berkeley; do
  for shard in 0 1; do
    U=$(echo $school | tr a-z A-Z)
    env LPCAP_LOCAL_$U=$S/wb-$school-$shard.sqlite nice -n 5 ${CS_ATLAS_PY} -I $T/autospec.py wayback $school $shard 2 > $T/logs/wayback-$school-$shard.log 2>&1 &
  done
done
wait
