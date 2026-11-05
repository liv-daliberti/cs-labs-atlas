#!/bin/bash
# Qwen3-Embedding-4B (and any model too large for the RTX 2080 lanes) on node105's RTX A5000 (24 GB): owner 2026-11-04 "run on node 105".
# SHARD/OF (default 0/1) pick shard SHARD of OF exactly as embed.py --shard/--of (sha1(id) % OF): lanes never overlap and finished work is skipped.
# EMB_BUDGET_SCALE multiplies the padded-token batch budget of models.py (sized for 8 GB 2080s); 2 is safe on the 24 GB A5000.
#   MODEL=nomic_v15 KIND=fulltext SHARD=1 OF=3 EMB_BUDGET_SCALE=2 sbatch embed-a5000.slurm
# One GPU, resumable (embed.py resumes by text hash; a part is never started after EMB_BUDGET seconds). CMD=selftest runs the fp16/fp32 check first.
#   CMD=selftest MODEL=qwen3_4b sbatch embed-a5000.slurm
#   MODEL=qwen3_4b KIND=abstract sbatch embed-a5000.slurm      (then KIND=fulltext)
#SBATCH --job-name=emb-a5000
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --nodelist=node105
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=2-00:00:00
#SBATCH --output=ai-writing/logs/emb-a5000-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
cd "$CS_ATLAS_AI_WRITING/embeddings"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
if [ "${CMD:-run}" = selftest ]; then
  $CS_ATLAS_ENV_PY -u embed.py selftest --model "${MODEL:?}"
else
  $CS_ATLAS_ENV_PY -u embed.py run --model "${MODEL:?}" --kind "${KIND:?}" --shard "${SHARD:-0}" --of "${OF:-1}" --budget "${EMB_BUDGET:-169000}"
fi
