#!/bin/bash
# Person-website live fetch (tools/person_fetch.py): robots-honouring, paced, live only; one school per job. usage: atlas submit hierarchy/person-fetch.slurm gatech
#SBATCH --job-name=person-fetch
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:59:00
#SBATCH --output=hierarchy/logs/person-fetch-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place; submit from the code root
cd "$CS_ATLAS_WORK"
# per-job scratch for page-1 PDFs and per-host stamps (never /n/fs); node805's shared /tmp was full on 2026-10-30 (not by
# us: the job's private /tmp was empty), so check df first and fall back to /dev/shm
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"
avail=$(df --output=avail -k /tmp | tail -1)
if [ "${avail:-0}" -lt 2000000 ]; then echo "/tmp has ${avail} kB free: using /dev/shm"; export TMPDIR=/dev/shm/$USER-$SLURM_JOB_ID; fi
mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
df -h "$TMPDIR" | tail -1
# run the code of ONE commit (docs/CONTRIBUTING.md, "Slurm jobs run from a code snapshot"); submit with `atlas submit` to pin it
# (the snapshot lives in $TMPDIR, which the trap above removes)
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
PY="$CS_ATLAS_PY"
for s in "$@"; do
  echo "== $s $(date -Is)"
  nice "$PY" -u "$CS_ATLAS_TOOLS/person_fetch.py" "$s" --workers 8 --deadline 3000 || echo "!! $s failed"
done
