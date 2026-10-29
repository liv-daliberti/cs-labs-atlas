#!/bin/bash
# AI-written-text detector: generate LLM versions of pre-ChatGPT abstracts with one model (gen.py generate <model> --tp N).
#SBATCH --job-name=aiw-gen
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/logs/gen-%j.out
#SBATCH --cpus-per-task=8
set -euo pipefail
ROOT=/n/fs/resemble/maxent-grpo
cd /n/fs/resemble/cs-atlas/work/ai-writing
export LD_LIBRARY_PATH="/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0
export TMPDIR=/tmp/aiw_${SLURM_JOB_ID}; mkdir -p $TMPDIR
/n/fs/resemble/cs-atlas-env/py310/bin/python -u gen.py generate "$1" --tp "${2:-1}"
