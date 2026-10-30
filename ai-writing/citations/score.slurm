#!/bin/bash
# v1 abstract detector on cited works: one shard per array task (score.py score SHARD NSHARDS).
# Submit: sbatch --array=0-2 score.slurm TAG 3
#SBATCH --job-name=cit-score
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=00:55:00
#SBATCH --output=ai-writing/citations/logs/score-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_AI_WRITING}/citations
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export TRITON_CACHE_DIR=${TMPDIR:-/tmp}/triton-$USER OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-6}
echo "{\"node\": \"$(hostname)\", \"shard\": \"${SLURM_ARRAY_TASK_ID}\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
${CS_ATLAS_ENV_PY} -u -B score.py score "$1" "${SLURM_ARRAY_TASK_ID}" "$2" 2>&1 | { grep -v -E "tensorflow|cudart|dso_loader" || true; }
