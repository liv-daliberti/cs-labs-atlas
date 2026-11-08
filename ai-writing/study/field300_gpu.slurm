#!/bin/bash
# GPU layers of the field-300 study on the abstracts of work/field300-2026-11-08/emb/texts.sqlite (field300_prep.py): the SAME models as the 12-school study.
#   sbatch --array=0-K%P field300_gpu.slurm embed MODEL   # embed.py run: shard = array task of F300_NSH shards, parts of 3000 abstracts (fp16 npz), resumable; stops at the budget, resubmit to resume
#   sbatch --array=0-K%P field300_gpu.slurm detect        # dose_score.py abstract: v1 abstract detector (p_v1; flag = p_v1 >= thr_abstract of the sealed 12-school snapshot) + v2 paragraph model
# One A5000 (24 GB), the card the 12-school embedding and detector jobs ran on (bf16 detector calibration); 59 minutes so the job routes through the shared pool.
#SBATCH --job-name=f300-gpu
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/logs/f300-gpu-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-/n/fs/resemble/homogenizing-science/code}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
export OMP_NUM_THREADS=6
WORK=${FIELD300_WORK:-/n/fs/resemble/homogenizing-science/studies/homogenization/work/field300-2026-11-08}
NSH=${F300_NSH:?number of shards}
SH=${SLURM_ARRAY_TASK_ID:-0}
AIW=${F300_AIW:-$CS_ATLAS_AI_WRITING}
export CS_ATLAS_EMBEDDINGS=$WORK/emb CS_ATLAS_AI_SCORES=$WORK/ai
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
case "${1:?embed|detect}" in
  embed)
    export EMB_BUDGET_SCALE=2
    cd "$AIW/embeddings"
    $CS_ATLAS_ENV_PY -u embed.py run --model "${2:?model}" --kind abstract --shard "$SH" --of "$NSH" --budget ${F300_BUDGET:-3000} ;;
  detect)
    cd "$AIW/dose"
    $CS_ATLAS_ENV_PY -u dose_score.py abstract --shard "$SH" --nshards "$NSH" --tag f300 ;;
esac
