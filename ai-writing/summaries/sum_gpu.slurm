#!/bin/bash
# summarize.py run on one A6000 (Qwen2.5-14B-Instruct bf16, TP=1). Array task id = entropy-32 shard. Resumable: done papers are skipped,
# exit 75 = stopped for budget (rerun to continue).    SHARDS="0 1" IDS=pilot_ids.json TAG=pilot sbatch sum_gpu.slurm   (pilot)
#SBATCH --job-name=sum14b
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --gres=gpu:a6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --exclude=node206
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-20261123/logs/sum-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=${SUM_V1:-0}
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} TMPDIR=/tmp/sum14b-${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR $TRITON_CACHE_DIR' EXIT
cd /n/fs/resemble/homogenizing-science/worktrees/summaries-14b/ai-writing/summaries
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-${SUM_ID:-20261123}
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
# 2026-11-23: node206 handed out a card with ~36 GB held by foreign processes (both pilot-2 runs OOMed). Refuse a card that is not empty.
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
[ "${used:-0}" -lt 2000 ] || { echo "{\"refused_gpu\": \"$(hostname)\", \"used_mib\": $used}"; exit 3; }
rc=0
for s in ${SHARDS:-$SLURM_ARRAY_TASK_ID}; do
  $CS_ATLAS_ENV_PY -u summarize.py run --shard "$s" ${IDS:+--ids $W/$IDS} ${TAG:+--tag $TAG} --budget "${SUM_BUDGET:-3000}" || rc=$?
done
exit $rc
