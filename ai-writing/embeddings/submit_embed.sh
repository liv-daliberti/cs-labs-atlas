#!/bin/bash
# Queue a chain of 59-minute embedding tasks for each shard of one (model, kind): task r of a shard starts after task r-1 ends (afterany), so a
# shard keeps one GPU busy until its todo is empty; tasks that find nothing to do exit at once. Never more than GPUS shards at a time in total:
# the script refuses when this user already has GPUS or more emb-run tasks running or queued as chain heads.
#   [AFTER=<jobid>] submit_embed.sh <model> <kind> <shards> <chain-length> [--dry]
# --test-only is run first, and nothing is submitted when the scheduler answers "Preempts:".
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/paths.sh" || exit 1
D="$(cd "$(dirname "$0")" && pwd)"
model=${1:?model}; kind=${2:?abstract|fulltext}; shards=${3:?shards}; chain=${4:?chain length}
GPUS=${GPUS:-8}
live=$(squeue -u "$USER" -h -n emb-run -o "%T %r" | grep -vc "Dependency" || true)   # running + queued chain heads; tasks held on a dependency are not GPUs yet
if [ "$((live + shards))" -gt "$GPUS" ]; then echo "{\"refused\": \"$live GPU tasks running or queued + $shards shards > $GPUS\"}"; exit 0; fi
# mltheory's RTX 2080 nodes only (node915-917; never node302 or node105): a task under an hour is routed through the shared pool, which also holds other groups'
# 2080 Ti nodes, so every node outside node915-917 is excluded on the command line (it overrides the script's --exclude).
EX=$(sinfo -h -N -p all -o %N | sort -u | grep -vE '^node91[5-7]$' | paste -sd,)
export OF=$shards MODEL=$model KIND=$kind
for ((s = 0; s < shards; s++)); do
  prev="${AFTER:-}"   # AFTER=<job id>: the chain waits for that job (a lane that runs several things one after another)
  for ((r = 0; r < chain; r++)); do
    dep=(); [ -z "$prev" ] || dep=(--dependency=afterany:$prev)
    t=$(SHARD=$s sbatch --test-only --exclude="$EX" "${dep[@]}" --export=ALL,SHARD=$s "$D/embed.slurm" 2>&1 || true)
    case "$t" in *Preempts:*) echo '{"refused": "scheduler would preempt"}'; exit 1 ;; esac
    [ "${5:-}" = "--dry" ] && { prev=dry$r; continue; }
    prev=$(SHARD=$s sbatch --parsable --exclude="$EX" "${dep[@]}" --export=ALL,SHARD=$s "$D/embed.slurm")
  done
  echo "{\"model\": \"$model\", \"kind\": \"$kind\", \"shard\": $s, \"last_job\": \"$prev\", \"chain\": $chain}"
done
