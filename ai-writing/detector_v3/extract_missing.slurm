#!/bin/bash
# detector v3: extract the copies that sections.sqlite lacks, one array task per shard (extract_missing.py).
#SBATCH --job-name=aiw3-extract
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v3/logs/extract-%A_%a.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v3
export PYTHONDONTWRITEBYTECODE=1 LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "{\"node\": \"$(hostname)\", \"shard\": ${SLURM_ARRAY_TASK_ID}}"
${CS_ATLAS_ENV_PY} -u -B extract_missing.py --shard ${SLURM_ARRAY_TASK_ID} --nshards ${NSHARDS} -j ${SLURM_CPUS_PER_TASK:-8}
