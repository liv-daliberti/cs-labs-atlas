#!/bin/bash
# CUHK D-0077: fetch department profiles for the research-statement check (tools/cuhk_statement_fetch.py); names file in $NAMES.
#SBATCH --job-name=cuhk-statement-fetch
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=hierarchy/logs/cuhk-statement-fetch-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"; mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
nice "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/cuhk_statement_fetch.py" "${NAMES:?}"
