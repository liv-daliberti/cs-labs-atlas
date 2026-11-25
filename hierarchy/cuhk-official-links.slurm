#!/bin/bash
# CUHK stage 3 (2026-11-25): re-discover the 15 PIs whose website was found through DBLP/ORCID, evaluating every candidate (profile pages too),
# so the official profile -> website link is a dated check. Names come from the file in $NAMES (one per line). Live-first, robots honoured.
#SBATCH --job-name=cuhk-official-links
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:58:00
#SBATCH --output=hierarchy/logs/cuhk-official-links-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"; mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
mapfile -t PIS < "${NAMES:?}"
nice "$CS_ATLAS_PY" -I -u "$CS_ATLAS_TOOLS/labpage_audit.py" discover cuhk --pi "${PIS[@]}" --redo --no-first-stop --live-first
nice "$CS_ATLAS_PY" -I -u "$CS_ATLAS_TOOLS/labpage_audit.py" audit cuhk
