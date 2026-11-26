#!/bin/bash
# e32.py gpu: detector v3 on every main/appendix passage + SPECTER2 base on the main body, one shard. One A5000 (the card v3 was calibrated on).
#SBATCH --job-name=e32-gpu
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/gpu-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u e32.py gpu --id "${E32_ID:-20261123}" --shard "$SLURM_ARRAY_TASK_ID" --budget 3100
