#!/bin/bash
#SBATCH --job-name=defense-gatech-live
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:58:00
#SBATCH --exclude=node302,node014
#SBATCH --output=fulltext-push/logs/defense-gatech-live-%j.out
# 2026-11-07 Georgia Tech PhD-defense announcements (hg.gatech.edu, robots: Disallow /node/add/ only; fulltext-push/defense_crawl.py), one request / 3 s.
# A chain of 58-minute jobs (--dependency=singleton): the first indexes the listing (resumable), every job then fetches event pages until 55 minutes are used.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
timeout -s TERM 3000 "$FTP_PY" -I -u defense_crawl.py index < /dev/null
timeout -s TERM 3150 "$FTP_PY" -I -u defense_crawl.py crawl < /dev/null
echo '{"defense-gatech-live": "job done"}'
