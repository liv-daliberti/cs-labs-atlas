#!/bin/bash
# texts.py <abstracts|fulltext>: the abstracts table (needs oa_fields.sqlite) or the full-text bodies (pdftotext for the copies not yet extracted).
#   sbatch texts.slurm fulltext      (CPU: 16 workers)      sbatch texts.slurm abstracts
#SBATCH --job-name=emb-texts
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node105
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/emb-texts-%j.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CS_ATLAS_AI_WRITING/embeddings"
$CS_ATLAS_ENV_PY -u texts.py "${1:?abstracts|fulltext}" -j "${SLURM_CPUS_PER_TASK:-8}"
