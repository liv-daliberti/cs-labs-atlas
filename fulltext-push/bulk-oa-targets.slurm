#!/bin/bash
#SBATCH --job-name=bulkoa-targets
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/bulk-oa-targets-%j.out
# 2026-11-04 the targets table of the bulk open-access channels (fulltext-push/bulk_oa.py). Submit from the code root.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_CODE"
$CS_ATLAS_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/bulk_oa.py" targets ${SCHOOLS:-princeton cmu epfl mit berkeley stanford michigan uchicago gatech}
