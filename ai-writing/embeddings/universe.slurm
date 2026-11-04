#!/bin/bash
# Build EMB/universe.sqlite (universe.py build): the paper list of the study. Light (reads the packages), so a small CPU job.
#SBATCH --job-name=emb-universe
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=ai-writing/logs/emb-universe-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/embeddings"
$CS_ATLAS_ENV_PY -u universe.py build
