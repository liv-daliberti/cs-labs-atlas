#!/bin/bash
#SBATCH --job-name=bulkoa-report
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:40:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/bulk-oa-report-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_CODE"
$CS_ATLAS_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/bulk_oa_report.py" report
for c in oa_locations core_bulk arxiv_bulk s2_bulk wayback_escholarship; do echo "== sample $c"; $CS_ATLAS_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/bulk_oa_report.py" sample $c 20 1; done
