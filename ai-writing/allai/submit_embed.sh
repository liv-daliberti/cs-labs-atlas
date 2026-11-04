#!/bin/bash
# Embed the rewrites with several models on node105's A5000s: one lane (one GPU at a time) per argument "style:model,model,...", each model a chain of
# 59-minute tasks (afterany), the next model of the lane starting after the previous chain. Never more than 3 lanes (owner's cap of 3 A5000s).
#   submit_embed.sh polish:specter2_base,specter2_proximity,scincl polish:qwen3_0p6b,bge_m3 polish:gte_qwen2_1p5b,nomic_v15      [CHAIN=3]
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "$#" -le 3 ] || { echo "at most 3 lanes"; exit 1; }
for lane in "$@"; do
  style=${lane%%:*}; prev=""
  for m in $(echo "${lane#*:}" | tr ',' ' '); do
    for ((r = 0; r < ${CHUNK_LEN:-3}; r++)); do
      dep=(); [ -z "$prev" ] || dep=(--dependency=afterany:$prev)
      opts=(--from-worktree --time=00:59:00 --partition=all --nodelist=node105 --exclude=node302 --gres=gpu:a5000:1 --mem=24G "${dep[@]}")
      t=$(MODEL=$m STYLE=$style bin/atlas submit "${opts[@]}" --test-only ai-writing/allai/embed.slurm 2>&1 || true)
      case "$t" in *Preempts:*) echo '{"refused": "scheduler would preempt"}'; exit 1 ;; esac
      prev=$(MODEL=$m STYLE=$style bin/atlas submit "${opts[@]}" --parsable ai-writing/allai/embed.slurm 2>/dev/null | tail -1)
    done
    echo "{\"style\": \"$style\", \"model\": \"$m\", \"last_job\": \"$prev\"}"
  done
done
