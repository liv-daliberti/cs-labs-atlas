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
RESTART_LOG="$CS_ATLAS_FT_LOGS/lab_first_loop-$s.out"
# the loop runs as a child so USR1 near the time limit can stop it and resubmit this task (loop_job.sh); TERM from scancel stops it for good
run_restartable "fulltext-push/downloads.slurm" "--array=$SLURM_ARRAY_TASK_ID" -- \
  nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u lab_first_loop.py $s --recent-first 2023 "${PRIORITY_ARGS[@]}" >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 < /dev/null
