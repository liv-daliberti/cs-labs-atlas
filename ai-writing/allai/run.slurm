#!/bin/bash
# Any CPU script of ai-writing/allai on the project's ML interpreter: run.slurm <script.py> [args]
#SBATCH --job-name=allai-run
#SBATCH --partition=all
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/allai-run-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/allai"
$CS_ATLAS_ENV_PY -u -B "$@"
