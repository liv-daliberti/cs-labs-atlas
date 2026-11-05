#!/bin/bash
# detector v3 on one GPU: detector3.py train|score --tag T [--holdout FAMILY]; resumable, chain with --dependency.
#SBATCH --job-name=aiw3-det
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v3/logs/det-%j.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v3
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
echo "{\"node\": \"$(hostname)\", \"args\": \"$*\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
${CS_ATLAS_ENV_PY} -u -B detector3.py "$@" --budget 44 2>&1 | { grep --line-buffered -v -E "tensorflow|cudart|dso_loader" || true; }
