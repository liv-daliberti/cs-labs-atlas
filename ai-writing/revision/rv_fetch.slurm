#!/bin/bash
# One array task of rv_fetch.py chunk: downloads and extracts its share of the planned v1/final PDFs (bucket copy, never arxiv.org). Resumable by chunk files.
#   sbatch --array=0-31%16 rv_fetch.slurm 32
#SBATCH --job-name=rv-fetch
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/rv-fetch-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
export SNAPSHOT_REPO="${SNAPSHOT_REPO:-${SLURM_SUBMIT_DIR:?}}"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/revision"
$CS_ATLAS_ENV_PY -u rv_fetch.py chunk "${SLURM_ARRAY_TASK_ID:-0}" "${1:?ntasks}"
