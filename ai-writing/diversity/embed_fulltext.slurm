#!/bin/bash
# Full-text SPECTER2 embeddings (embed_fulltext.py run): one A5000 (bf16), resumable chunks, < 59 minutes per job.
# Never on a 2080 Ti (no bf16). Submitted by submit_embed.sh, which keeps at most 2 of these in the queue.
#SBATCH --job-name=aiw-divemb
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/diversity/logs/emb-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
PY=${CS_ATLAS_ENV_PY}
export LD_LIBRARY_PATH="$(dirname "$(readlink -f "$PY")")/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
export TRITON_CACHE_DIR=/tmp/aiw-divemb-triton-$SLURM_JOB_ID
cd ${CS_ATLAS_AI_WRITING}/diversity
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$PY -u embed_fulltext.py run --budget "${BUDGET:-3000}"
