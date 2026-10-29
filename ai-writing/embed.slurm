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
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_AI_WRITING"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export THREADS=${SLURM_CPUS_PER_TASK:-32}
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
$CS_ATLAS_ENV_PY -u embed.py
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
