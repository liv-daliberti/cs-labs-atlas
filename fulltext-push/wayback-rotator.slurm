#!/bin/bash
# Rotating single Wayback fetcher (2026-11-16, owner): see wayback_rotate.py. 1 CPU, 1 G; every minute one decision, one squeue. Exactly one school's loop
# runs with WAYBACK_HOLD=0 at a time (about an hour each); every other loop keeps WAYBACK_HOLD=1.
# Submit: WAYBACK_ROTATE_ADOPT=gatech atlas submit fulltext-push/wayback-rotator.slurm   (ADOPT: the loop that already runs unheld becomes the first turn)
# Restarts itself like the loops (USR1 900 s before the limit: the child keeps the turn in logs/wayback-rotation-state.json and is resubmitted).
# KILL SWITCH: `scancel -n wayback-rotator` (SIGTERM): the holder is re-held (scancel + held resubmit) before this job exits, and the rotator is NOT resubmitted.
# After a hard kill (node loss, SIGKILL): run `wayback_rotate.py rehold` (python -I via CS_ATLAS_PY, from fulltext-push/) to re-hold whoever is unheld.
#SBATCH --job-name=wayback-rotator
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/wayback-rotator-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
RESTART_LOG="$CS_ATLAS_FT_LOGS/wayback-rotator.restarts"
# not run_restartable: its TERM and USR1 both send TERM to the child, and the child must tell a scancel (re-hold the holder, stop) from the time-limit
# restart (keep the turn). USR1 -> python SIGUSR1 (save state, exit); TERM/INT -> python SIGTERM (re-hold, exit).
"$CS_ATLAS_PY" -I -u wayback_rotate.py run &
CHILD=$!
RESTART=
trap 'RESTART=1; kill -USR1 "$CHILD" 2>/dev/null' USR1
trap 'kill -TERM "$CHILD" 2>/dev/null' TERM INT
rc=0
while kill -0 "$CHILD" 2>/dev/null; do wait "$CHILD"; rc=$?; done
trap - TERM INT USR1
if [ -n "$RESTART" ]; then
  _restart_log "\"time limit near: rotator stopped (exit $rc), turn state kept, resubmitting\""
  _resubmit "fulltext-push/wayback-rotator.slurm"
fi
exit "$rc"
