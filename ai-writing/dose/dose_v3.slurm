#!/bin/bash
# CPU job of the detector-v3 rerun (owner 2026-11-05): dose_v3.slurm <script.py> [args...]; runs against the v3 container (dose_build_v3.py).
# Submit:  atlas submit --partition=all --account=mltheory --exclude=node302,node014,node805,node808 --cpus-per-task=16 --mem=64G --time=00:59:00 --output=<log> dose_v3.slurm ...
#SBATCH --job-name=ai-dose-v3
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:59:00
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export CS_ATLAS_AI_SCORES="${AI_SCORES_V3_DIR:-$CS_ATLAS_CODE/ai-writing/data/ai-scores-v3}" AI_DETECTOR=v3
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
cd "$CS_ATLAS_AI_WRITING/dose"
S=${1:?script}; shift
$CS_ATLAS_ENV_PY -u "$S" "$@"
