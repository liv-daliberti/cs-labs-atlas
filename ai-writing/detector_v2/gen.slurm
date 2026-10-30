#!/bin/bash
# Passage-level detector v2: AI versions of the source passages with one generator (gen.py generate <gen> --tp N).
#SBATCH --job-name=aiw2-gen
#SBATCH --output=ai-writing/detector_v2/logs/gen-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
PY=${CS_ATLAS_ENV_PY}
cd ${CS_ATLAS_AI_WRITING}/detector_v2
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/tmp/aiw2_${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR' EXIT
echo "{\"node\": \"$(hostname)\", \"gen\": \"$1\", \"tp\": \"${2:-1}\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
$PY -u -B gen.py generate "$1" --tp "${2:-1}"
