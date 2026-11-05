#!/bin/bash
# CPU jobs of the lab-level study: labstudy.slurm <script.py> [args...]   (frame, ipw, topic_convergence, event_study, ...)
# Standing rules: partition all, account mltheory, <= 59 min, --exclude node302,node014,node805,node808, explicit cpus/mem/time (override with sbatch flags).
#SBATCH --job-name=labstudy
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/labstudy-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-16} OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-16} PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
cd "$CS_ATLAS_AI_WRITING/labstudy"
S=${1:?script}; shift
$CS_ATLAS_ENV_PY -u "$S" "$@"
