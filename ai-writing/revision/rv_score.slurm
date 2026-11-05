#!/bin/bash
# GPU scoring of the v1/final texts (rv_score.py). Resumable by text hash. Detector is a parameter: DETECTOR=v2 (default) or v3.
#   sbatch --array=0-7%4 --gres=gpu:<model>:1 rv_score.slurm <nshards>            e.g. 8 shards
#SBATCH --job-name=rv-score
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=40G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/rv-score-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
export SNAPSHOT_REPO="${SNAPSHOT_REPO:-${SLURM_SUBMIT_DIR:?}}"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} OMP_NUM_THREADS=6
cd "$CS_ATLAS_AI_WRITING/revision"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u rv_score.py --detector "${DETECTOR:-v2}" --shard "${SLURM_ARRAY_TASK_ID:-0}" --nshards "${1:?nshards}" --tag "${TAG:-r$(date +%Y%m%d)}"
