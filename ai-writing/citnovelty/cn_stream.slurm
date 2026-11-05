#!/bin/bash
# One task of the citation-study stream pass (cn_stream.py filter): streams its share of the OpenAlex works parts from S3, accumulates citation counts.
# Prepare once:  cn_stream.py prepare          Submit: sbatch --array=0-127%32 cn_stream.slurm        Merge: sbatch cn_stream.slurm merge
# Tasks are idempotent (a finished task has a .done file and is skipped), so a failed array is simply resubmitted.
#SBATCH --job-name=cn-stream
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/cn-stream-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
export SNAPSHOT_REPO="${SNAPSHOT_REPO:-${SLURM_SUBMIT_DIR:?}}"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/citnovelty"
OF="${CN_OF:-128}"
if [ "${1:-filter}" = merge ]; then
  $CS_ATLAS_ENV_PY -u cn_stream.py merge --of "$OF"
else
  $CS_ATLAS_ENV_PY -u cn_stream.py filter "${SLURM_ARRAY_TASK_ID:-0}" "$OF"
fi
