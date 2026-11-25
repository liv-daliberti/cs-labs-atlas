#!/bin/bash
# CUHK stage 3: re-discover the PIs named in $NAMES (one per line), then merge. Wayback only where the charter / D-0076 says so; one writer per school store.
#SBATCH --job-name=cuhk-rediscover
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --output=hierarchy/logs/cuhk-rediscover-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"; mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
mapfile -t PIS < "${NAMES:?}"
nice "$CS_ATLAS_PY" -I -u "$CS_ATLAS_TOOLS/labpage_audit.py" discover cuhk --pi "${PIS[@]}" --redo
