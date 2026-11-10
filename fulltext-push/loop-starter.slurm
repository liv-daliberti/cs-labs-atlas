#!/bin/bash
# Light, self-restarting starter for the download loops of the big stores (2026-11-10): see loop_starter.py. 1 CPU, 1 G.
# Submit: SCHOOL=loopstarter SCHOOLS="stanford berkeley princeton epfl mit cmu" atlas submit fulltext-push/loop-starter.slurm   (exits when all are started)
#SBATCH --job-name=loop-starter
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/loop-starter-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
: "${SCHOOLS:?set SCHOOLS}"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
refuse_if_downloads_stopped
RESTART_LOG="$CS_ATLAS_FT_LOGS/loop-starter.restarts"
export LOOP_STARTER_SCHOOLS="$SCHOOLS"
run_restartable "fulltext-push/loop-starter.slurm" -- "$CS_ATLAS_COLLECTOR_PY" -I -u loop_starter.py $SCHOOLS
