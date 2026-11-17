#!/bin/bash
# Evidence-store backups as a light, self-restarting Slurm job (R3b, 2026-11-17), the shape of disk-guard.slurm: 1 CPU, 1 G. Every 15 minutes it backs up each
# store-sourced school (charter [evidence] source = "store") whose newest backup is older than 24 h: sqlite online backup + integrity_check + sha256 into
# archive/evidence-store-backups/<UTC stamp>/, newest 14 per school kept; skipped while the share has under 50 GB free. See docs/EVIDENCE-STORE.md.
# Submit: atlas submit fulltext-push/evidence-backup.slurm   Restarts itself (USR1 900 s before the limit, loop_job.sh); scancel stops it for good.
#SBATCH --job-name=evidence-backup
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/evidence-backup-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
RESTART_LOG="$CS_ATLAS_FT_LOGS/evidence-backup.restarts"
export LOOP_RESUBMIT_IGNORE_STOP=1
run_restartable "fulltext-push/evidence-backup.slurm" -- "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/evidence_store.py" backup --loop
