#!/bin/bash
# detector v3: AI versions with one open generator (gen3.py generate <gen> [--tp N]); resumable, resubmit to continue.
#SBATCH --job-name=aiw3-gen
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v3/logs/gen-%j.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v3
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/tmp/aiw3_${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR' EXIT
echo "{\"node\": \"$(hostname)\", \"gen\": \"$1\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
${CS_ATLAS_ENV_PY} -u -B gen3.py generate "$1" --tp "${2:-1}" --budget 40 2>&1 | grep --line-buffered -v -E "tensorflow|cudart|dso_loader"
