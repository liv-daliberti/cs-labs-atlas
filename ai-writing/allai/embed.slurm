#!/bin/bash
# One GPU task embedding the REWRITTEN abstracts (texts_<STYLE>.sqlite) with one model into the store <MODEL>__allai (polish) / <MODEL>__para (paraphrase),
# so originals and rewrites never share a container. Resumable and sharded like embeddings/embed.slurm. Defaults to mltheory's RTX 2080s (<= 59 min);
# for the A5000: sbatch --nodelist=node105 --gres=gpu:a5000:1 --time=... (qwen3_4b needs it).
#   MODEL=qwen3_0p6b STYLE=polish OF=1 SHARD=0 sbatch embed.slurm
#SBATCH --job-name=allai-emb
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --gres=gpu:rtx_2080:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-emb-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=true
cd "$CS_ATLAS_AI_WRITING/embeddings"
STYLE=${STYLE:-polish}; case "$STYLE" in polish) SUF=__allai;; polish_dropped) SUF=__allaix;; *) SUF=__para;; esac
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
$CS_ATLAS_ENV_PY -u embed.py run --model "${MODEL:?}" --kind abstract --shard "${SHARD:-0}" --of "${OF:-1}" --budget "${EMB_BUDGET:-3150}" \
  --store-name "${MODEL}${SUF}" --texts-db "$CS_ATLAS_EMBEDDINGS/allai/texts_${STYLE}.sqlite"
