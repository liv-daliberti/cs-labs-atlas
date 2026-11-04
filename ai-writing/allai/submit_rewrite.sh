#!/bin/bash
# Chains of 59-minute rewrite tasks per shard on node105 (a task under an hour is routed through partition all and starts when a card frees up).
#   submit_rewrite.sh <style> <shards> <chain> [--subsample]     run from the worktree/checkout: uses atlas submit --from-worktree
set -euo pipefail
style=${1:?}; of=${2:?}; chain=${3:?}; sub=${4:+1}
cd "$(dirname "$0")/../.."
for ((s = 0; s < of; s++)); do
  prev=""
  for ((r = 0; r < chain; r++)); do
    dep=(); [ -z "$prev" ] || dep=(--dependency=afterany:$prev)
    opts=(--from-worktree --time=00:59:00 --partition=all --nodelist=node105 "${dep[@]}")
    t=$(STYLE=$style OF=$of SHARD=$s RW_BUDGET=2900 SUBSAMPLE=$sub bin/atlas submit "${opts[@]}" --test-only ai-writing/allai/rewrite.slurm 2>&1 || true)
    case "$t" in *Preempts:*) echo '{"refused": "scheduler would preempt"}'; exit 1 ;; esac
    prev=$(STYLE=$style OF=$of SHARD=$s RW_BUDGET=2900 SUBSAMPLE=$sub bin/atlas submit "${opts[@]}" --parsable ai-writing/allai/rewrite.slurm 2>/dev/null | tail -1)
  done
  echo "{\"style\": \"$style\", \"shard\": $s, \"last_job\": \"$prev\", \"chain\": $chain}"
done
