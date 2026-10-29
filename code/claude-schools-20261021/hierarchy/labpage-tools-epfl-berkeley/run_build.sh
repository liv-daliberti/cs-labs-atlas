#!/bin/bash
# Build both schools' outputs offline from the capture stores, then merge any rows copied from sister stores.
T=/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/labpage-tools-epfl-berkeley
S=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb; mkdir -p $S
for s in epfl berkeley; do
  LPCAP_OFFLINE=1 $T/lpc.sh c8 lpbuild.py $s --write > $T/logs/build-$s.log 2>&1
done
for s in epfl berkeley; do /usr/local/anaconda3/2024.02/bin/python -I $T/merge.py $s $S/c8-$s.sqlite $S/c10-$s.sqlite >> $T/logs/build-merge.log 2>&1; done
echo BUILD-DONE >> $T/logs/build-merge.log
