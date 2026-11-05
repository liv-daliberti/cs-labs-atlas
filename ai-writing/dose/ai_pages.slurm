#!/bin/bash
# AI-pages data stages (ai_pages.py): ai_pages.slurm <stage> [args...]   (frame, umap, labs, matched, fig3; CPU only, no GPU)
#SBATCH --job-name=ai-pages
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/ai-pages-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
cd "$CS_ATLAS_AI_WRITING/dose"
S=${1:?stage}; shift
$CS_ATLAS_ENV_PY -u ai_pages.py "$S" "$@"
