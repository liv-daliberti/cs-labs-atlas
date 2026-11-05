#!/bin/bash
# AI-written vs not on every metric (ai_vs_not.py): ai_vs_not.slurm model --model M   |   ai_vs_not.slurm assemble   (CPU only)
#SBATCH --job-name=ai-vs-not
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-vs-not-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
cd "$CS_ATLAS_AI_WRITING/dose"
$CS_ATLAS_ENV_PY -u ai_vs_not.py "$@"
