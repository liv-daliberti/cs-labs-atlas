#!/bin/bash
# Cold-scan only: fill <store>/.copy-quality-cache.jsonl for SCHOOLS (in order) so the download loops start fast (fulltext-push/warm_copy_cache.py).
# Restartable like the loops (USR1 900 s before the limit -> resubmit with the same SCHOOLS; a finished school is a quick metadata pass on restart).
# Two chains at a time at most (NFS load). Submit: SCHOOLS="michigan stanford" atlas submit fulltext-push/warm-copy-cache.slurm
#SBATCH --job-name=warm-copy-cache
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/warm-copy-cache-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
: "${SCHOOLS:?set SCHOOLS}"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
refuse_if_downloads_stopped
RESTART_LOG="$CS_ATLAS_FT_LOGS/warm-copy-cache.restarts"
run_restartable "fulltext-push/warm-copy-cache.slurm" -- nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u warm_copy_cache.py $SCHOOLS
