#!/bin/bash
# One-off: download the embedding models into env/hf-cache (network + a few GB of sequential writes; no GPU).
#SBATCH --job-name=emb-download
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-download-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" HF_HOME=$CS_ATLAS_HF_HOME
cd "$CS_ATLAS_AI_WRITING/embeddings"
$CS_ATLAS_ENV_PY -u download_models.py "$@"
