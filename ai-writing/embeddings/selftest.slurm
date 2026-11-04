#!/bin/bash
# fp16 vs fp32 check of one or more models on an RTX 2080 (embed.py selftest): selftest.slurm <model> [<model> ...]
#SBATCH --job-name=emb-selftest
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --gres=gpu:rtx_2080:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-selftest-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
cd "$CS_ATLAS_AI_WRITING/embeddings"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
for m in "$@"; do $CS_ATLAS_ENV_PY -u embed.py selftest --model "$m" 2>&1 | grep -v Warning | tail -25 || echo "{\"selftest\": \"$m\", \"crashed\": true}"; done
