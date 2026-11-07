#!/bin/bash
# detector v3 section rescoring, one array task per shard: score_sections.py --shard $SLURM_ARRAY_TASK_ID --nshards $NSHARDS [...]
#SBATCH --job-name=aiw3-secscore
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v3/logs/secscore-%A_%a.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v3
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HF_HOME=${CS_ATLAS_HF_HOME} HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
echo "{\"node\": \"$(hostname)\", \"shard\": ${SLURM_ARRAY_TASK_ID}, \"nshards\": ${NSHARDS}, \"gpus\": \"${CUDA_VISIBLE_DEVICES:-}\"}"
${CS_ATLAS_ENV_PY} -u -B score_sections.py --shard ${SLURM_ARRAY_TASK_ID} --nshards ${NSHARDS} --tag ${TAG:-all} ${CONTAINERS:+--containers $CONTAINERS} 2>&1 | grep --line-buffered -v -E "tensorflow|cudart|dso_loader"
