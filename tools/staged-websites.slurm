#!/bin/bash
# Staged-school website sweep (tools/staged_websites.py): robots-honouring, paced, live; one or more schools per job. usage: atlas submit tools/staged-websites.slurm purdue
#SBATCH --job-name=staged-websites
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:59:00
#SBATCH --output=hierarchy/logs/staged-websites-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place; submit from the code root
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"
avail=$(df --output=avail -k /tmp | tail -1)
if [ "${avail:-0}" -lt 2000000 ]; then echo "/tmp has ${avail} kB free: using /dev/shm"; export TMPDIR=/dev/shm/$USER-$SLURM_JOB_ID; fi
mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
df -h "$TMPDIR" | tail -1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
PY="$CS_ATLAS_PY"
for s in "$@"; do
  echo "== $s $(date -Is)"
  nice "$PY" -u "$CS_ATLAS_TOOLS/staged_websites.py" build "$s" --workers 12 --deadline 3200 --out-dir "${STAGED_OUT:?set STAGED_OUT to the worktree hierarchy dir}/$s/reviewed" || echo "!! $s failed"
done
