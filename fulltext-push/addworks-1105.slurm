#!/bin/bash
# 2026-11-05: the OpenAlex refresh (tools/oa_refresh_works.py) added 2025-2026 works and lab papers that no catalog holds. The live packages
# are rebuilt only by the next release, so add_works.py reads a SCRATCH hierarchy root (CS_ATLAS_HIERARCHY): live raw/reviewed/work dirs and derived
# files by symlink, except lab_papers.jsonl.gz, which is the refresh's scratch rebuild (AFTER=<scratch>/build-after/<school>/lab_papers.jsonl.gz).
# Then: add_works.py per school (queued works), Princeton's package through import_all_when_free.py, and every open-copy channel for the seven
# released schools (as addworks-1104.slurm; CORE stays paused; Michigan never uses Deep Blue). uchicago and gatech get add_works only (no channel run:
# their channel lists are not reviewed). The download loops (downloads.slurm) then fetch.
#SBATCH --job-name=fulltext-addworks
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=6
#SBATCH --mem=28G
#SBATCH --time=2-00:00:00
#SBATCH --output=fulltext-push/logs/addworks-1105-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
: "${AFTER:?AFTER=<scratch>/build-after}"
LIVE=$CS_ATLAS_HIERARCHY
ROOT=${AFTER%/*}/hierarchy-addworks
SCHOOLS_ALL="princeton cmu epfl mit berkeley stanford michigan uchicago gatech"
for s in $SCHOOLS_ALL; do
  mkdir -p "$ROOT/$s/derived" || exit 1
  for d in raw reviewed work reports; do [ -e "$LIVE/$s/$d" ] && ln -sfn "$LIVE/$s/$d" "$ROOT/$s/$d"; done
  for f in "$LIVE/$s/derived"/*; do b=$(basename "$f"); [ "$b" = lab_papers.jsonl.gz ] || ln -sfn "$f" "$ROOT/$s/derived/$b"; done
  ln -sfn "$AFTER/$s/lab_papers.jsonl.gz" "$ROOT/$s/derived/lab_papers.jsonl.gz"
done
export CS_ATLAS_HIERARCHY=$ROOT
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in $SCHOOLS_ALL; do
  echo "== add_works $s $(date +%T)"
  "${CS_ATLAS_COLLECTOR_PY}" -u add_works.py "$s" || echo "{\"failed\": \"add_works $s\"}"
done
PKG=$(ls -d "$CS_ATLAS_STORES"/princeton/discovery/claude-labpapers-newworks-* 2>/dev/null | tail -1)
[ -d "$PKG" ] && nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" "cs_pi_works:$(basename "$PKG")"
COMMON="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages pihomes wayback_acm"
./run_steps.sh princeton oar $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1 < /dev/null &
./run_steps.sh cmu $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-cmu.log 2>&1 < /dev/null &
./run_steps.sh epfl $COMMON infoscience >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1 < /dev/null &
./run_steps.sh mit $COMMON dspace >> "$CS_ATLAS_FT_LOGS"/steps-mit.log 2>&1 < /dev/null &
./run_steps.sh berkeley $COMMON techrpt pubpages >> "$CS_ATLAS_FT_LOGS"/steps-berkeley.log 2>&1 < /dev/null &
./run_steps.sh stanford $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-stanford.log 2>&1 < /dev/null &
./run_steps.sh michigan $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-michigan.log 2>&1 < /dev/null &
wait
echo '{"addworks_1105": "done"}'
