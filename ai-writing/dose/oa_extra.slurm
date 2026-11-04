#!/bin/bash
# One task of the OpenAlex reference/OA-status pass (oa_extra.py filter): streams its share of the works partitions from S3, keeps the universe's works.
# Submit: sbatch --array=0-63%16 oa_extra.slurm   (CPU only; 64 tasks of 2 CPUs, 59 minutes each so they route to the shared pool); then universe.slurm-style merge: see README.md.
#SBATCH --job-name=ai-dose-oaextra
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-dose-oaextra-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/dose"
if [ "${1:-filter}" = merge ]; then
  $CS_ATLAS_ENV_PY -u oa_extra.py merge --of "${OA_OF:-64}"
else
  $CS_ATLAS_ENV_PY -u oa_extra.py filter "${SLURM_ARRAY_TASK_ID:-0}" "${OA_OF:-64}"
fi
