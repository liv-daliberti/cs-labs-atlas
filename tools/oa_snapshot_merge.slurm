#!/bin/bash
# Merge the 16 filter parts into OA_SNAPSHOT/<date>/openalex.sqlite and remove them. Submit after the filter array:
#   OA_DATE=2026-10-14 atlas submit --dependency=afterok:<array id> tools/oa_snapshot_merge.slurm
#SBATCH --job-name=oa-snapshot-merge
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=fulltext-push/logs/oa-snapshot-merge-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
: "${OA_DATE:?set OA_DATE}"
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_snapshot.py" merge --date "$OA_DATE" --of 16 ${OA_NO_PROMOTE:+--no-promote}
