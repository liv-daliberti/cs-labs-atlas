#!/bin/bash
# Disk guard as a light, self-restarting Slurm job (2026-11-10): 1 CPU, 1 G; every 2 minutes `df -B1G` of the project share and, under 250 GB, touch
# raw/downloads_stopped_by_disk_guard + `scancel --name=<our download job names>` (all nodes). See disk_guard.py. Submit: atlas submit fulltext-push/disk-guard.slurm
# Restarts itself like the loops (USR1 900 s before the limit, loop_job.sh); scancel stops it for good. It resubmits even while the marker exists.
#SBATCH --job-name=disk-guard
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/disk-guard-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
RESTART_LOG="$CS_ATLAS_FT_LOGS/disk-guard.restarts"
export LOOP_RESUBMIT_IGNORE_STOP=1
run_restartable "fulltext-push/disk-guard.slurm" -- "$CS_ATLAS_PY" -I -u disk_guard.py
