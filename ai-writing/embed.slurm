#!/bin/bash
# embed.py (abstract SPECTER2, incremental, CPU) on a compute node: only new or changed title+abstract texts are embedded.
#SBATCH --job-name=aiw-absemb
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/logs/absemb-%j.out
set -euo pipefail
cd /n/fs/resemble/cs-atlas/work/ai-writing
export LD_LIBRARY_PATH="/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=/n/fs/resemble/cs-atlas-env/hf-cache HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export THREADS=${SLURM_CPUS_PER_TASK:-32}
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
/n/fs/resemble/cs-atlas-env/py310/bin/python -u embed.py
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
