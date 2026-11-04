#!/bin/bash
# One GPU task of embed.py run on mltheory's RTX 2080s (8 GB, Turing: fp16, no bf16, no flash-attention). Resumable; shards are disjoint.
#   MODEL=qwen3_0p6b KIND=abstract OF=4 sbatch --array=0-3 embed.slurm        (see submit_embed.sh, which also throttles to <= 8 GPUs)
# Never node302 (A100) or node105 (A5000).
#SBATCH --job-name=emb-run
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --gres=gpu:rtx_2080:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=2-00:00:00
#SBATCH --output=ai-writing/logs/emb-run-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
cd "$CS_ATLAS_AI_WRITING/embeddings"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u embed.py run --model "${MODEL:?}" --kind "${KIND:?}" --shard "${SLURM_ARRAY_TASK_ID:-0}" --of "${OF:-1}" --budget "${EMB_BUDGET:-165000}"
