#!/bin/bash
# The snapshot-vs-API proof (docs/OPENALEX-SNAPSHOT.md section 10): atlas submit tools/oa_snapshot_compare.slurm
#SBATCH --job-name=oa-snapshot-compare
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=fulltext-push/logs/oa-snapshot-compare-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
"$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_snapshot_compare.py" counts
for s in ${FIELD_SCHOOLS:-epfl}; do "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_snapshot_compare.py" fields "$s" --n 1000; done
