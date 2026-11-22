#!/bin/bash
#SBATCH --job-name=wayback-acm-vol
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=03:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/wayback-acm-vol-%j.out
# 2026-11-21 channel wayback_acm_vol (fulltext-push/channels/wayback_acm_vol.py) for each school in SCHOOLS, in that order (the most ACM papers
# first). One process asks web.archive.org at a time (run_steps-wayback_acm_vol.lock), through the shared slot (host_throttle).
# 2026-11-22: one Wayback fetcher at a time (owner rule). The rotator yields every download turn while a job named like a Wayback fetcher is
# RUNNING, so a lookup job that runs for days lets no Wayback copy be downloaded. This job therefore takes turns with the downloads: it asks for
# RUN_S seconds (default 90 min; a run cut short loses nothing, every answer is cached as it comes), then exits and resubmits itself to start
# GAP_S later (default 90 min, PENDING, so the rotator grants a download turn meanwhile). A run that stops on a 429 or a long shared cooldown
# ends this turn early. When every school had nothing left to ask, no successor is submitted. Submit with `atlas submit` from the code root.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
S=${SCHOOLS:?SCHOOLS (most ACM papers first)}
LAST="${TMPDIR:-/tmp}/wayback-acm-vol-$SLURM_JOB_ID.last"; trap 'rm -f "$LAST"' EXIT
END=$(( $(date +%s) + ${RUN_S:-5400} ))
open=0
for s in $S; do
  left=$(( END - $(date +%s) ))
  [ "$left" -le 120 ] && { open=1; break; }
  ( flock 9; timeout -s INT "$left" nice -n 5 $CS_ATLAS_PY -I -u channel_runner.py $s wayback_acm_vol ${DRY:+--dry} ) \
      9>>"$CS_ATLAS_FT_LOGS"/run_steps-wayback_acm_vol.lock 2>&1 < /dev/null | tee "$LAST"
  tail -1 "$LAST" | grep -q '"wayback_acm_vol_papers_to_ask": 0,' || open=1   # asked something, was cut short, or stopped: more to do
  tail -1 "$LAST" | grep -q '"stopped"' && break                                 # the archive is cooling down for every client
done
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"turn_done\": true, \"more_to_ask\": $open}"
if [ "$open" = 1 ] && [ -z "$DRY" ] && [ "${NO_RESUBMIT:-0}" != 1 ]; then
  cd "${SLURM_SUBMIT_DIR:?}" && sbatch --parsable --begin="now+${GAP_S:-5400}" \
      --export=ALL,CS_ATLAS_SNAPSHOT_COMMIT="${CS_ATLAS_SNAPSHOT_COMMIT:-}" fulltext-push/wayback-acm-vol.slurm \
      | sed 's/^/{"next_turn_job": "/; s/$/"}/'
else
  echo '{"wayback-acm-vol": "done"}'
fi
