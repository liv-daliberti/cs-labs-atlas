#!/bin/bash
# One GPU task of rewrite.py run on node105's RTX A5000 (24 GB; Qwen2.5-7B-Instruct in bf16 needs ~16 GB). Resumable, shards are disjoint.
#   STYLE=polish OF=3 SHARD=0 sbatch rewrite.slurm        (STYLE=paraphrase SUBSAMPLE=1 for the 5,000-paper robustness style)
#SBATCH --job-name=allai-rw
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --nodelist=node105
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=ai-writing/logs/allai-rw-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false VLLM_USE_V1=0 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/tmp/allai_${SLURM_JOB_ID}; mkdir -p $TMPDIR; trap 'rm -rf $TMPDIR' EXIT
cd "$CS_ATLAS_AI_WRITING/allai"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u rewrite.py run --style "${STYLE:-polish}" --shard "${SHARD:-0}" --of "${OF:-1}" ${SUBSAMPLE:+--subsample} ${LIMIT:+--limit $LIMIT} --budget "${RW_BUDGET:-1000000000}"
