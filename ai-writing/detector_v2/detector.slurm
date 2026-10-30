#!/bin/bash
# Passage-level detector v2 on one GPU: train (detector.py train [--holdout GEN] [--save]) or score a shard
# (detector.py score --shard I --nshards N; the shard index is SLURM_ARRAY_TASK_ID, and each task reads one contiguous
# rowid range of ai-writing/fulltext.sqlite in place).
#SBATCH --job-name=aiw2-det
#SBATCH --output=ai-writing/detector_v2/logs/det-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
PY=${CS_ATLAS_ENV_PY}
D=${CS_ATLAS_AI_WRITING}/detector_v2
cd $D
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
echo "{\"node\": \"$(hostname)\", \"args\": \"$*\", \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
if [ "$1" = score ]; then
  $PY -u -B detector.py score --shard "${SLURM_ARRAY_TASK_ID}" --nshards "$2" 2>&1 | { grep -v -E "tensorflow|cudart|dso_loader" || true; }
else
  $PY -u -B detector.py "$@" 2>&1 | { grep -v -E "tensorflow|cudart|dso_loader" || true; }
fi
