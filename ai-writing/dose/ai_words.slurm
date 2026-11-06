#!/bin/bash
# AI marker words (ai_words_site.py): ai_words.slurm <stage> [args...]   (count, liang, assemble, spot; CPU only)
#SBATCH --job-name=ai-words
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/scratch/ai-words-20261105/ai-words-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1
cd "$CS_ATLAS_AI_WRITING/dose"
S=${1:?stage}; shift
$CS_ATLAS_ENV_PY -u ai_words_site.py "$S" "$@"
