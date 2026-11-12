#!/bin/bash
# OpenReview student route (R-STU-27, tools/openreview_students.py): name-first profile search for the self-declared candidates of each school.
# Paced (>= 6 s between requests across processes), cached (a request is never repeated), resumable: re-submit and the cache answers what was
# done. One chunk <= 55 min of work; the job exits 0 on budget/time end (re-submit) and 3 when the host stopped us (HTTP 429/401/403/challenge): then
# do NOT re-submit the same UTC day. Only one such job at a time (the 6 s gap is shared through a lock file, but the owner's account is one account).
# Check with `sbatch --test-only` first; submit with `atlas submit`.
# usage: sbatch tools/openreview_students.slurm hkust [sjtu ...]      (BUDGET=450 per school by default; ARGS="--all" adds PIs with >= 3 students)
#SBATCH --job-name=or-students
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=hierarchy/logs/openreview-students-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK" 2>/dev/null || cd "$CS_ATLAS_CODE"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
PY="$CS_ATLAS_PY"
rc=0
for s in "$@"; do
  "$PY" "$CS_ATLAS_CODE/tools/openreview_students.py" run "$s" --budget "${BUDGET:-450}" --max-minutes 50 ${ARGS:-}
  r=$?
  if [ "$r" -eq 3 ]; then echo "stopped by the host: not continuing"; rc=3; break; fi
done
exit $rc
