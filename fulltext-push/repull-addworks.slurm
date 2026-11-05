#!/bin/bash
# ROADMAP #51: the end-of-day copy step of the trickled OpenAlex re-pull (tools/oa_repull_trickle.py queues it after each day's chunks, serialized by
# --dependency=singleton, behind any running cs-release). Like addworks-1105.slurm: the day's new lab papers have no catalog work yet. A SCRATCH rebuild of the
# touched schools' packages (PI_HIERARCHY_OUT; nothing live is written, this is not a release) gives lab_papers.jsonl.gz; add_works.py then runs on a scratch
# hierarchy root of symlinks to the live dirs plus that file, and the open-copy channels run for the touched released schools. CORE stays paused.
#   SCHOOLS=princeton+cmu (the schools with new works that day), DAY=2026-11-06
#SBATCH --job-name=cs-repull-addworks
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=4
#SBATCH --mem=40G
#SBATCH --time=2-00:00:00
#SBATCH --output=fulltext-push/logs/repull-addworks-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
: "${SCHOOLS:?SCHOOLS=a+b}" "${DAY:?DAY=YYYY-MM-DD}"
SCHOOLS=${SCHOOLS//+/ }
LIVE=$CS_ATLAS_HIERARCHY
BASE=$CS_ATLAS_SCRATCH/oa-repull-trickle/addworks-$DAY
ROOT=$BASE/hierarchy
export PYTHONHASHSEED=0
for s in $SCHOOLS; do
  echo "== scratch build $s $(date +%T)"
  PI_HIERARCHY_OUT="$BASE/build" nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$s" || { echo "{\"failed\": \"build $s\"}"; continue; }
  mkdir -p "$ROOT/$s/derived" || exit 1
  for d in raw reviewed work reports; do [ -e "$LIVE/$s/$d" ] && ln -sfn "$LIVE/$s/$d" "$ROOT/$s/$d"; done
  for f in "$LIVE/$s/derived"/*; do b=$(basename "$f"); [ "$b" = lab_papers.jsonl.gz ] || ln -sfn "$f" "$ROOT/$s/derived/$b"; done
  ln -sfn "$BASE/build/$s/lab_papers.jsonl.gz" "$ROOT/$s/derived/lab_papers.jsonl.gz"
done
export CS_ATLAS_HIERARCHY=$ROOT
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in $SCHOOLS; do
  [ -e "$ROOT/$s/derived/lab_papers.jsonl.gz" ] || continue
  echo "== add_works $s $(date +%T)"
  "${CS_ATLAS_COLLECTOR_PY}" -u add_works.py "$s" || echo "{\"failed\": \"add_works $s\"}"
done
COMMON="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages pihomes wayback_acm"
for s in $SCHOOLS; do
  case $s in
    princeton)
      PKG=$(ls -d "$CS_ATLAS_STORES"/princeton/discovery/claude-labpapers-newworks-* 2>/dev/null | tail -1)
      [ -d "$PKG" ] && nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" "cs_pi_works:$(basename "$PKG")"
      X="oar" ;;
    epfl) X="infoscience" ;;
    mit) X="dspace" ;;
    berkeley) X="techrpt pubpages" ;;
    cmu|stanford|michigan) X="" ;;
    *) continue ;;      # uchicago, gatech: add_works only (their channel lists are not reviewed)
  esac
  # princeton's oar comes before the common channels, the others' extras after (as addworks-1105.slurm)
  if [ "$s" = princeton ]; then ./run_steps.sh "$s" $X $COMMON >> "$CS_ATLAS_FT_LOGS/steps-$s.log" 2>&1 < /dev/null &
  else ./run_steps.sh "$s" $COMMON $X >> "$CS_ATLAS_FT_LOGS/steps-$s.log" 2>&1 < /dev/null &
  fi
done
wait
echo "{\"repull_addworks\": \"done\", \"day\": \"$DAY\"}"
