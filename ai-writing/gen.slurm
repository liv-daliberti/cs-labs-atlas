#!/bin/bash
# AI-written-text detector: generate LLM versions of pre-ChatGPT abstracts with one model (gen.py generate <model> --tp N).
#SBATCH --job-name=aiw-gen
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/logs/gen-%j.out
#SBATCH --cpus-per-task=8
set -euo pipefail
ROOT=/n/fs/resemble/maxent-grpo
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_AI_WRITING"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0
export TMPDIR=/tmp/aiw_${SLURM_JOB_ID}; mkdir -p $TMPDIR
$CS_ATLAS_ENV_PY -u gen.py generate "$1" --tp "${2:-1}"
