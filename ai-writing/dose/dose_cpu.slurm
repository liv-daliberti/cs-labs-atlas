#!/bin/bash
# CPU jobs of the AI-dose study: dose_cpu.slurm <script.py> [args...]   (kobak, liang, build, validate, analysis ...)
#SBATCH --job-name=ai-dose-cpu
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-dose-cpu-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
cd "$CS_ATLAS_AI_WRITING/dose"
S=${1:?script}; shift
$CS_ATLAS_ENV_PY -u "$S" "$@"
