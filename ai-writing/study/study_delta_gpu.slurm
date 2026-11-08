#!/bin/bash
# GPU steps of the snapshot delta (study_delta_build.py): abstract embeddings of the delta papers with all seven models, the v1 abstract detector, or the v3 passage scoring.
#   sbatch study_delta_gpu.slurm embed       # seven models, abstracts (bf16/fp16 as embed.py), parts + merge into WORK/emb
#   sbatch study_delta_gpu.slurm abstract    # v1 abstract detector (dose_score.py abstract), bf16 -> needs Ampere; the A5000 is the card both detectors were calibrated on
#   sbatch study_delta_gpu.slurm score       # detector v3 on the main/appendix passages (study_delta_build.py score)
# One A5000 (24 GB; nothing here needs more), 59 minutes so the job routes through the shared pool; resumable (embed.py skips done text hashes, score/abstract skip finished output).
#SBATCH --job-name=study-delta-gpu
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --gres=gpu:a5000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/logs/study-delta-gpu-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-/n/fs/resemble/homogenizing-science/code}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=$CS_ATLAS_HF_HOME HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
export OMP_NUM_THREADS=6
BASE=${DELTA_BASE:-2026-11-07}
WORK=/n/fs/resemble/homogenizing-science/studies/homogenization/work/delta-$BASE
STUDY=${STUDY_CODE:-/n/fs/resemble/homogenizing-science/worktrees/ai-share/ai-writing/study}
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
case "${1:?embed|abstract|score}" in
  embed)
    export CS_ATLAS_EMBEDDINGS=$WORK/emb EMB_BUDGET_SCALE=2
    cd "$CS_ATLAS_AI_WRITING/embeddings"
    for M in specter2_proximity specter2_base scincl nomic_v15 bge_m3 qwen3_0p6b gte_qwen2_1p5b; do
      $CS_ATLAS_ENV_PY -u embed.py run --model $M --kind abstract --budget 3000
      $CS_ATLAS_ENV_PY -u embed.py merge --model $M --kind abstract
    done ;;
  abstract)
    export CS_ATLAS_EMBEDDINGS=$WORK/emb CS_ATLAS_AI_SCORES=$WORK/ai
    cd "$CS_ATLAS_AI_WRITING/dose"
    $CS_ATLAS_ENV_PY -u dose_score.py abstract --shard 0 --nshards 1 --hi 1000000000 --tag delta ;;
  score)
    export PYTHONPATH="$CS_ATLAS_TOOLS:$STUDY"
    cd "$STUDY"
    $CS_ATLAS_ENV_PY -u study_delta_build.py score --id "$BASE" ;;
esac
