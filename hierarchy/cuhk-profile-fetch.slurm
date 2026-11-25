#!/bin/bash
# CUHK stage 3: live-fetch the department profiles the faculty directory links for PIs whose website has no recorded official link (tools/cuhk_profile_fetch.py).
#SBATCH --job-name=cuhk-profile-fetch
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:40:00
#SBATCH --output=hierarchy/logs/cuhk-profile-fetch-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"; mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
nice "$CS_ATLAS_PY" -I -u "$CS_ATLAS_TOOLS/cuhk_profile_fetch.py" "${REGISTER:?}"
