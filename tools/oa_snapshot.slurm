#!/bin/bash
# The OpenAlex snapshot filter: 16 array tasks, each streams its share of the parts (no raw dump on disk) and leaves one part file in
# SCRATCH. Submit:  OA_DATE=2026-10-14 atlas submit tools/oa_snapshot.slurm   then the merge with --dependency=afterok:<id>
# (tools/oa_snapshot_merge.slurm). Plan and sizes: docs/OPENALEX-SNAPSHOT.md.
#SBATCH --job-name=oa-snapshot-filter
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --array=0-15
#SBATCH --output=fulltext-push/logs/oa-snapshot-%A_%a.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
: "${OA_DATE:?set OA_DATE to the snapshot date (the manifest date)}"
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_snapshot.py" filter "$SLURM_ARRAY_TASK_ID" 16 --date "$OA_DATE"
