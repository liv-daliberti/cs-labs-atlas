#!/bin/bash
# Fold a model's finished parts into the school containers (embed.py merge): merge.slurm <model> <kind> [<model> <kind> ...]. CPU only; loads every part.
#SBATCH --job-name=emb-merge
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-merge-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/embeddings"
while [ $# -ge 2 ]; do $CS_ATLAS_ENV_PY -u embed.py merge --model "$1" --kind "$2"; shift 2; done
