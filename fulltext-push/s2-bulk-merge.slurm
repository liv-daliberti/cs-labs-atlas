#!/bin/bash
#SBATCH --job-name=s2-bulk-merge
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/s2-bulk-merge-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_CODE"
$CS_ATLAS_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/s2_bulk.py" merge ${DATASET:-papers}
