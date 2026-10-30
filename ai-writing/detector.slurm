#!/bin/bash
# AI-written-text detector: train (detector.py train [--holdout MODEL]) or score (detector.py score) on one GPU.
#SBATCH --job-name=aiw-det
#SBATCH --output=ai-writing/logs/det-%j.out
#SBATCH --cpus-per-task=8
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_AI_WRITING"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
$CS_ATLAS_ENV_PY -u detector.py "$@"
