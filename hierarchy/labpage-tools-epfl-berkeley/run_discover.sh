#!/bin/bash
# Discovery shards for the lab-page pass; each shard writes its own local capture DB (merged later by merge.py).
T=/n/fs/resemble/cs-atlas/work/hierarchy/labpage-tools-epfl-berkeley
S=/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/lpdb
for school in epfl berkeley; do
  for shard in 0 1 2; do
    U=$(echo $school | tr a-z A-Z)
    env LPCAP_LOCAL_$U=$S/discover-$school-$shard.sqlite nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I $T/discover.py $school $shard 3 > $T/logs/discover-$school-$shard.log 2>&1 &
  done
done
wait
