#!/bin/bash
#SBATCH --job-name=etd-crawl
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=7-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/etd-crawl-%j.out
# 2026-11-04 polite crawl of dissertation item pages for the adviser field (fulltext-push/etd_crawl.py): SCHOOL=gatech|uchicago.
# One request every >= 10 s, one host, resumable (resubmit to continue). Evidence is built afterwards: etd_crawl.py evidence <school>.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
"$FTP_PY" -I -u etd_crawl.py crawl "${SCHOOL:?SCHOOL}" < /dev/null
echo '{"etd-crawl": "done"}'
