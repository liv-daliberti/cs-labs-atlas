#!/bin/bash
# Coverage counter (lab_paper_copies.py) and, with LEDGER=1, the unavailability ledger (--offline: no network, no new checks) for SCHOOLS, written into a
# SCRATCH hierarchy root (CS_ATLAS_HIERARCHY): the live derived files stay untouched (2026-11-10, downloads task). Read-only on the stores.
# SCRATCH_ROOT overrides the root; the symlink farm is built here, copies.json and the ledger files are fresh. Submit: SCHOOLS="harvard jhu washu" LEDGER=1 atlas submit fulltext-push/copies-isolated.slurm
#SBATCH --job-name=copies-isolated
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --output=fulltext-push/logs/copies-isolated-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
: "${SCHOOLS:?set SCHOOLS}"
LIVE=$CS_ATLAS_HIERARCHY
ROOT=${SCRATCH_ROOT:-$CS_ATLAS_ROOT/scratch/downloads-1110/hierarchy}
for s in $SCHOOLS; do
  mkdir -p "$ROOT/$s/derived" || exit 1
  for d in raw reviewed work reports; do [ -e "$LIVE/$s/$d" ] && ln -sfn "$LIVE/$s/$d" "$ROOT/$s/$d"; done
  for f in "$LIVE/$s/derived"/*; do b=$(basename "$f"); case $b in copies.json|unavailable.jsonl.gz|unavailable-summary.json) ;; *) ln -sfn "$f" "$ROOT/$s/derived/$b";; esac; done
done
export CS_ATLAS_HIERARCHY=$ROOT
cd "$CS_ATLAS_WORK"
nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u "$CS_ATLAS_TOOLS/lab_paper_copies.py" $SCHOOLS
[ "${LEDGER:-0}" = 1 ] && nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u "$CS_ATLAS_FULLTEXT_PUSH/unavailable_ledger.py" $SCHOOLS --offline
echo "scratch results under $ROOT/<school>/derived/ ; live ones are unchanged"
