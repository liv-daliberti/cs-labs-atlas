#!/bin/bash
# detect.py score on one GPU (ModernBERT-large, bf16). STYLE=polish sbatch detect.slurm
#SBATCH --job-name=allai-det
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-det-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/tmp/allai_det_${SLURM_JOB_ID}; mkdir -p $TMPDIR; export TRITON_CACHE_DIR=$TMPDIR/triton; trap 'rm -rf "$TMPDIR"' EXIT
cd "$CS_ATLAS_AI_WRITING/allai"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u -B detect.py score --style "${STYLE:-polish}" --originals "${ORIG:-1000}"
