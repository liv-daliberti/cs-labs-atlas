#!/bin/bash
# 2026-10-29: the lab-first download loop for each school, one array task per school (the per-school collector scripts
# also re-ran every open-copy channel; those finished on 10-29, so a restart only needs the loops).
#SBATCH --job-name=fulltext-downloads
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-6
#SBATCH --signal=B:USR1@900   # 15 min before the limit: stop the loop cleanly and resubmit this task (loop_job.sh, ROADMAP #18)
#SBATCH --output=fulltext-push/logs/downloads-%A_%a.out
SCHOOLS=(princeton cmu epfl mit berkeley stanford michigan)  # 6 = michigan (its channels finished 2026-10-31: the loop only)
s=${SCHOOLS[$SLURM_ARRAY_TASK_ID]}
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"  # compute nodes have no /usr/local/anaconda3; the project env has protego and bs4 (as michigan-collector.slurm)
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
# 2026-11-03 (owner): link-only papers still queued for download go first. The priority file is written from the latest release at every
# (re)start, so the USR1 self-restart picks up a newer release; a failure here only loses the ordering, never the loop.
PRIORITY="$CS_ATLAS_FT_RAW/$s-priority-work-ids.tsv"
${CS_ATLAS_COLLECTOR_PY} -I priority_file.py $s >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 || rm -f "$PRIORITY"
PRIORITY_ARGS=(); [ -s "$PRIORITY" ] && PRIORITY_ARGS=(--priority-file "$PRIORITY")
# 2026-11-03 (owner, download yield): the loop only asks the collector for candidates the catalog already holds, so two channels put the
# release's open copies there first: ledger_found (the ledger's new_open_urls: arXiv ids -> arXiv's bulk copy, PMC ids -> the PMC S3 files,
# URLs) and reader_link (the reader's confirmed link of each queued link-only paper). Both skip a URL the work already knows; the collector
# still applies robots.txt, pacing and the title check. Princeton's channel writes a discovery package, imported as princeton_pass.sh does.
# A failure only loses the new candidates, never the loop.
if [ -s "$PRIORITY" ]; then
  ( flock 9; ${CS_ATLAS_COLLECTOR_PY} -I -u channel_runner.py $s ledger_found reader_link ) 9>>"$CS_ATLAS_FT_LOGS/run_steps-ledger_found.lock" >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 < /dev/null || true
  if [ "$s" = princeton ]; then
    pk=$(ls -d "$CS_ATLAS_STORES"/princeton/discovery/claude-labpapers-*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
    [ -n "$pk" ] && ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 < /dev/null || true
  fi
fi
RESTART_LOG="$CS_ATLAS_FT_LOGS/lab_first_loop-$s.out"
# the loop runs as a child so USR1 near the time limit can stop it and resubmit this task (loop_job.sh); TERM from scancel stops it for good
run_restartable "fulltext-push/downloads.slurm" "--array=$SLURM_ARRAY_TASK_ID" -- \
  nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u lab_first_loop.py $s --recent-first 2023 "${PRIORITY_ARGS[@]}" >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 < /dev/null
