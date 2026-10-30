#!/bin/bash
# embed.py (abstract SPECTER2, incremental, CPU) on a compute node: only new or changed title+abstract texts are embedded.
#SBATCH --job-name=aiw-absemb
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=32
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=ai-writing/logs/absemb-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_AI_WRITING"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export THREADS=${SLURM_CPUS_PER_TASK:-32}
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
$CS_ATLAS_ENV_PY -u embed.py
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
