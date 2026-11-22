#!/bin/bash
#SBATCH --job-name=wayback-acm-vol
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=3-00:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/wayback-acm-vol-%j.out
# 2026-11-21 channel wayback_acm_vol (fulltext-push/channels/wayback_acm_vol.py) for each school in SCHOOLS, in that order (the most ACM papers
# first). A pass stops at the first school whose run stopped. One process asks web.archive.org at a time (run_steps-wayback_acm_vol.lock), through the shared slot (host_throttle). A run that stops
# on a 429 or a long shared cooldown is retried in the next pass after PAUSE_S; every answer is cached, so a pass only asks what is still open
# and a finished school costs one catalog read. Candidates reach the loops' catalogs as the lookups go; downloads take the Wayback rotator's turn.
# Submit with `atlas submit` from the code root.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
S=${SCHOOLS:?SCHOOLS (most ACM papers first)}
LAST="${TMPDIR:-/tmp}/wayback-acm-vol-$SLURM_JOB_ID.last"; trap 'rm -f "$LAST"' EXIT
for pass in $(seq 1 ${PASSES:-8}); do
  open=0
  for s in $S; do
    ( flock 9; nice -n 5 $CS_ATLAS_PY -I -u channel_runner.py $s wayback_acm_vol ${DRY:+--dry} ) 9>>"$CS_ATLAS_FT_LOGS"/run_steps-wayback_acm_vol.lock 2>&1 | tee "$LAST"
    tail -1 "$LAST" | grep -q '"stopped"' && { open=1; break; }   # the archive is cooling down for every client: wait, then go on
  done
  echo "{\"pass\": $pass, \"at\": \"$(date -u +%FT%TZ)\", \"stopped_somewhere\": $open}"
  [ "$open" = 0 ] && break
  [ -n "$DRY" ] && break
  sleep ${PAUSE_S:-1200}
done
echo '{"wayback-acm-vol": "done"}'
