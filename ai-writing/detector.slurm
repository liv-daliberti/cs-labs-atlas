#!/bin/bash
# AI-written-text detector: train (detector.py train [--holdout MODEL]) or score (detector.py score) on one GPU.
#SBATCH --job-name=aiw-det
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/logs/det-%j.out
#SBATCH --cpus-per-task=8
set -euo pipefail
ROOT=/n/fs/resemble/maxent-grpo
cd /n/fs/resemble/cs-atlas/work/ai-writing
export LD_LIBRARY_PATH="/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
/n/fs/resemble/cs-atlas-env/py310/bin/python -u detector.py "$@"
