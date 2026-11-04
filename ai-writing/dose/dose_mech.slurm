#!/bin/bash
# Embed the human/AI wording pairs with one model (dose_mech.py embed). A5000 on node105 (<= 2 of its cards at a time) or an RTX 2080 lane:
#   MODEL=qwen3_4b sbatch dose_mech.slurm                                  (A5000, default)
#   MODEL=bge_m3 sbatch --partition=mltheory --account=mltheory --exclude=node302,node105 --nodelist= --gres=gpu:rtx_2080:1 dose_mech.slurm
#SBATCH --job-name=ai-dose-mech
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --nodelist=node105
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=40G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-dose-mech-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
cd "$CS_ATLAS_AI_WRITING/dose"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u dose_mech.py embed --model "${MODEL:?}"
