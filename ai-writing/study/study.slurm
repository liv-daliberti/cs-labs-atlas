#!/bin/bash
# One restartable step of the 12-school study: sbatch study.slurm <script.py> [args]   (study_delta_oa.py, study_analyze.py, ...)
#SBATCH --job-name=study1107
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/logs/study1107-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-/n/fs/resemble/homogenizing-science/code}/paths.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" MPLBACKEND=Agg OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
HERE=${STUDY_CODE:-/n/fs/resemble/homogenizing-science/worktrees/study-1107/ai-writing/study}
export PYTHONPATH="$HERE/../../tools:$HERE:$HERE/../labstudy"
cd "$HERE"
S=${1:?script}; shift
$CS_ATLAS_ENV_PY -u "$S" "$@"
