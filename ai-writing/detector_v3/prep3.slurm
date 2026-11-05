#!/bin/bash
# detector v3 data prep (CPU): prep3.py. Submit from the code root of the checkout that holds this file.
#SBATCH --job-name=aiw3-prep
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/ai-writing/detector_v3/logs/prep-%j.out
set -euo pipefail
. "${SLURM_SUBMIT_DIR:?}/paths.sh" || exit 1
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
cd ${SLURM_SUBMIT_DIR}/ai-writing/detector_v3
cp ${CS_ATLAS_AI_WRITING}/fulltext.sqlite /tmp/aiw3_fulltext_$SLURM_JOB_ID.sqlite
trap 'rm -f /tmp/aiw3_fulltext_$SLURM_JOB_ID.sqlite' EXIT
${CS_ATLAS_ENV_PY} -u -B prep3.py --db /tmp/aiw3_fulltext_$SLURM_JOB_ID.sqlite -j 14
