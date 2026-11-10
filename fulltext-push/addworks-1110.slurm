#!/bin/bash
# 2026-11-10: harvard, jhu and washu showed not_in_catalog for every lab paper in copies.json (counted 2026-11-07, before their catalogs were seeded).
# DRY=1 (default): add_works.py --dry for each school (counts only). DRY=0: add_works.py (queued works, under the catalog write lock), then the coverage counter
# into a SCRATCH hierarchy root (CS_ATLAS_HIERARCHY; live raw/reviewed/work/reports + derived files by symlink, only copies.json is fresh) so live derived files
# are not touched. SCHOOLS overrides the list. Submit: DRY=0 atlas submit fulltext-push/addworks-1110.slurm
#SBATCH --job-name=fulltext-addworks
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:59:00
#SBATCH --output=fulltext-push/logs/addworks-1110-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
S=${SCHOOLS:-harvard jhu washu}
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in $S; do
  echo "== add_works $s dry=${DRY:-1} $(date +%T)"
  if [ "${DRY:-1}" = 1 ]; then nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u add_works.py "$s" --dry
  else
    nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u addworks_guard.py before "$s" || { echo "{\"failed\": \"backup $s\"}"; continue; }
    nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u add_works.py "$s" || echo "{\"failed\": \"add_works $s\"}"
    nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u addworks_guard.py after "$s" || echo "{\"guard_failed\": \"$s\"}"
  fi
done
[ "${DRY:-1}" = 1 ] && exit 0
[ "${NO_RECOUNT:-0}" = 1 ] && exit 0
LIVE=$CS_ATLAS_HIERARCHY
ROOT=${SCRATCH_ROOT:-$CS_ATLAS_ROOT/scratch/downloads-1110/hierarchy}
for s in $S; do
  mkdir -p "$ROOT/$s/derived" || exit 1
  for d in raw reviewed work reports; do [ -e "$LIVE/$s/$d" ] && ln -sfn "$LIVE/$s/$d" "$ROOT/$s/$d"; done
  for f in "$LIVE/$s/derived"/*; do b=$(basename "$f"); [ "$b" = copies.json ] || ln -sfn "$f" "$ROOT/$s/derived/$b"; done
done
export CS_ATLAS_HIERARCHY=$ROOT
cd "$CS_ATLAS_WORK"
nice -n 5 "$CS_ATLAS_COLLECTOR_PY" -I -u "$CS_ATLAS_TOOLS/lab_paper_copies.py" $S
echo "scratch copies.json under $ROOT/<school>/derived/ ; live ones are unchanged"
