#!/bin/bash
# Personal websites of PIs and students (tools/person_sweep.py): STEP=fetch fetches the recorded URLs live (robots, >= 3 s per host,
# no e-mail address in the User-Agent); STEP=harvest re-reads the stored official pages. usage: STEP=fetch SHARD=0/4 atlas submit hierarchy/person-sweep.slurm princeton
#SBATCH --job-name=person-sweep
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:59:00
#SBATCH --output=hierarchy/logs/person-sweep-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place; submit from the code root
cd "$CS_ATLAS_WORK"
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"
mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1   # run the code of ONE commit
PY="$CS_ATLAS_PY"
for s in "$@"; do
  echo "== $s ${STEP:-fetch} $(date -Is)"
  nice "$PY" -u "$CS_ATLAS_TOOLS/person_sweep.py" "${STEP:-fetch}" "$s" --shard "${SHARD:-0/1}" || echo "!! $s ${STEP:-fetch} failed"
done
