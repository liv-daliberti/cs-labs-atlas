#!/bin/bash
# detector v4 on one GPU: detector4.py train|score --tag T --variant V [--holdout FAMILY]; resumable (checkpoints / score parts), chain with --dependency.
# Submit from the worktree root:  sbatch ... ai-writing/detector_v4/detector4.slurm train --tag t --variant tri --holdout qwen
#SBATCH --job-name=aiw4-det
#SBATCH --account=mltheory
#SBATCH --partition=all
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=59:00
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v4/logs/det-%j.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v4
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export PYTHONUTF8=1 LC_ALL=C.UTF-8
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
echo "{\"node\": \"$(hostname)\", \"args\": \"$*\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
${CS_ATLAS_ENV_PY} -u -B detector4.py "$@" $([ "$1" = train ] && echo --budget 44) 2>&1 | { grep --line-buffered -v -E "tensorflow|cudart|dso_loader" || true; }
