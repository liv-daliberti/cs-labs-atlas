#!/bin/bash
#SBATCH --job-name=bulkoa-report
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:40:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/bulk-oa-report-%j.out
. /n/fs/resemble/homogenizing-science/code/paths.sh
cd /n/fs/resemble/homogenizing-science/worktrees/bulk-oa
$CS_ATLAS_PY -I -u fulltext-push/bulk_oa_report.py report
for c in oa_locations core_bulk arxiv_bulk s2_bulk; do echo "== sample $c"; $CS_ATLAS_PY -I -u fulltext-push/bulk_oa_report.py sample $c 20 1; done
