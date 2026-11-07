#!/bin/bash
#SBATCH --job-name=etd-gatech-live
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:58:00
#SBATCH --exclude=node302,node014
#SBATCH --output=fulltext-push/logs/etd-gatech-live-%j.out
# 2026-11-07 Georgia Tech student gathering: the LIVE repository.gatech.edu item-page crawl (fulltext-push/etd_crawl.py, robots allows /entities/publication/,
# Crawl-delay 10, one flock per host) as a chain of 58-minute jobs (~330 pages each), submitted with --dependency=singleton. Resumable; the queue order is
# the lastmod tiers of docs/hierarchy/gatech/reports/STAGE-6.md. Evidence afterwards: etd_crawl.py evidence gatech.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
"$FTP_PY" -I -u etd_crawl.py crawl gatech --max "${MAX:-330}" < /dev/null
echo '{"etd-gatech-live": "job done"}'
