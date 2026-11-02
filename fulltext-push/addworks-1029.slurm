#!/bin/bash
# 2026-10-29: the hierarchy's lab_papers.jsonl.gz were regenerated (12:57-13:42 UTC) with ~4,800 lab papers no catalog
# work matches. add_works.py adds them (Princeton: a cs_pi_works package imported through import_all_when_free.py
# before any channel runs, so the channels see the works), then every channel runs for every school
# (run_steps.sh; per-channel locks; each step only touches works without a copy and URLs not yet known).
#SBATCH --job-name=fulltext-addworks
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=6
#SBATCH --mem=28G
#SBATCH --time=2-00:00:00
#SBATCH --output=fulltext-push/logs/addworks-1029-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_FULLTEXT_PUSH"
PY="nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u"
OUT=$CS_ATLAS_STORES/princeton
for s in princeton cmu epfl mit berkeley stanford; do $PY add_works.py $s; done
pk=$(ls -d $OUT/discovery/claude-labpapers-newworks-2026102913* $OUT/discovery/claude-labpapers-newworks-2026102914* $OUT/discovery/claude-labpapers-newworks-2026102915* $OUT/discovery/claude-labpapers-newworks-2026102916* $OUT/discovery/claude-labpapers-newworks-2026102917* $OUT/discovery/claude-labpapers-newworks-2026102918* 2>/dev/null | while read d; do echo "cs_pi_works:$(basename $d)"; done)
[ -n "$pk" ] && (nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk)
COMMON="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages"
./run_steps.sh princeton oar $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1 < /dev/null &
./run_steps.sh cmu $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-cmu.log 2>&1 < /dev/null &
./run_steps.sh epfl $COMMON infoscience >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1 < /dev/null &
./run_steps.sh mit $COMMON dspace >> "$CS_ATLAS_FT_LOGS"/steps-mit.log 2>&1 < /dev/null &
./run_steps.sh berkeley $COMMON techrpt pubpages >> "$CS_ATLAS_FT_LOGS"/steps-berkeley.log 2>&1 < /dev/null &
./run_steps.sh stanford $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-stanford.log 2>&1 < /dev/null &
wait
pk=$(ls -d $OUT/discovery/claude-labpapers-*-2026102[9]*/ $OUT/discovery/claude-labpapers-*-2026103*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk)
echo '{"addworks_1029": "done"}'
