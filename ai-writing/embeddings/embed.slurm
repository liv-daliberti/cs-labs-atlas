#!/bin/bash
# One GPU task of embed.py run on mltheory's RTX 2080s (8 GB, Turing: fp16, no bf16, no flash-attention). Resumable; shards are disjoint.
#   MODEL=qwen3_0p6b KIND=abstract OF=4 SHARD=2 sbatch embed.slurm        (submit_embed.sh queues chains of these per shard, <= 8 GPUs)
# Never node302 (A100) or node105 (A5000).
#SBATCH --job-name=emb-run
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --gres=gpu:rtx_2080:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-run-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
cd "$CS_ATLAS_AI_WRITING/embeddings"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u embed.py run --model "${MODEL:?}" --kind "${KIND:?}" --shard "${SHARD:-${SLURM_ARRAY_TASK_ID:-0}}" --of "${OF:-1}" --budget "${EMB_BUDGET:-3150}"
