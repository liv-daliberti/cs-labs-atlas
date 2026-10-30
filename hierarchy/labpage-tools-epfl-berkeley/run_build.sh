#!/bin/bash
# Build both schools' outputs offline from the capture stores, then merge any rows copied from sister stores.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
T=${CS_ATLAS_HIERARCHY}/labpage-tools-epfl-berkeley
S=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb; mkdir -p $S
for s in epfl berkeley; do
  LPCAP_OFFLINE=1 $T/lpc.sh c8 lpbuild.py $s --write > $T/logs/build-$s.log 2>&1
done
for s in epfl berkeley; do ${CS_ATLAS_PY} -I $T/merge.py $s $S/c8-$s.sqlite $S/c10-$s.sqlite >> $T/logs/build-merge.log 2>&1; done
echo BUILD-DONE >> $T/logs/build-merge.log
