#!/bin/bash
# GPU step of design 3 (study_design_revision_gpu.py): appendix passages of the arXiv versions, detector v3. One A5000 (the card the detector was calibrated on); restartable by chunk.
#   sbatch --array=0-5 study_design_revision_gpu.slurm <nshards>
#SBATCH --job-name=sd-revapp
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/logs/sd-revapp-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-/n/fs/resemble/homogenizing-science/code}/paths.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID} OMP_NUM_THREADS=6
HERE=${STUDY_CODE:?STUDY_CODE}
export PYTHONPATH="$HERE/../../tools:$HERE"
cd "$HERE"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u study_design_revision_gpu.py --id "${SNAPSHOT_ID:-2026-11-08}" --shard "${SLURM_ARRAY_TASK_ID:-0}" --nshards "${1:?nshards}"
