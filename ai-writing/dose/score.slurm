#!/bin/bash
# Detector scoring of every paper on node105's RTX A5000 (owner 2026-11-04: at most 2 A5000s of node105 at a time, 1-GPU jobs).
#   atlas submit --array=0-23%2 score.slurm fulltext 24 <hi>      (hi = max rowid of texts.sqlite fulltext, fixed at submit time)
#   atlas submit --array=0-3%2  score.slurm abstract 4  <hi>
# Resumable by text hash: a re-run scores only what is not in AI_SCORES/parts.
#SBATCH --job-name=ai-dose-score
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --nodelist=node105
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=40G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-dose-score-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
export OMP_NUM_THREADS=6
cd "$CS_ATLAS_AI_WRITING/dose"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
KIND=${1:?abstract|fulltext}; N=${2:?nshards}; HI=${3:-1000000000}
$CS_ATLAS_ENV_PY -u score.py "$KIND" --shard "${SLURM_ARRAY_TASK_ID:-0}" --nshards "$N" --hi "$HI" --tag "${TAG:-d20261104}"
