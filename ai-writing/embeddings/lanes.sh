#!/bin/bash
# The full-text lane program: 8 lanes (GPUs), lane i runs shard i of 8 of every model in turn, each as a chain of 59-minute tasks
# (afterany). Lengths are in tasks, from the measured rates (tokens/s on an RTX 2080 Ti): SPECTER2 ~60k, Nomic ~14k, BGE-M3 ~13k, Qwen3-0.6B ~6k, GTE-Qwen2-1.5B ~3k.
# A task that finds its shard done exits at once, so an over-long chain costs only queue time. Submit from the code root after exporting
# SNAPSHOT_REPO / CS_ATLAS_SNAPSHOT_COMMIT.   usage: lanes.sh [<lane> ...]   (default 0..7)   LANES_MODELS="m:chain m:chain ..." overrides the program
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
PROGRAM=${LANES_MODELS:-"specter2_base:2 specter2_proximity:2 nomic_v15:4 bge_m3:4 qwen3_0p6b:7 gte_qwen2_1p5b:12"}
for lane in ${@:-0 1 2 3 4 5 6 7}; do
  prev=""
  for item in $PROGRAM; do
    m=${item%%:*}; n=${item##*:}
    out=$(AFTER=$prev ONLY_SHARD=$lane GPUS=${GPUS:-8} "$D/submit_embed.sh" "$m" fulltext 8 "$n")
    echo "$out"
    prev=$(echo "$out" | sed -n 's/.*"last_job": "\([0-9]*\)".*/\1/p' | tail -1)
    [ -n "$prev" ] || { echo "{\"lane\": $lane, \"stopped_at\": \"$m\"}"; break; }
  done
done
