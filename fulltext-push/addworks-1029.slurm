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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/addworks-1029-%j.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push
PY="nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u"
PRIN=/n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015
OUT=/n/fs/resemble/homogenizing-science/data/fulltext/princeton
for s in princeton cmu epfl mit berkeley stanford; do $PY add_works.py $s; done
pk=$(ls -d $OUT/discovery/claude-labpapers-newworks-2026102913* $OUT/discovery/claude-labpapers-newworks-2026102914* $OUT/discovery/claude-labpapers-newworks-2026102915* $OUT/discovery/claude-labpapers-newworks-2026102916* $OUT/discovery/claude-labpapers-newworks-2026102917* $OUT/discovery/claude-labpapers-newworks-2026102918* 2>/dev/null | while read d; do echo "cs_pi_works:$(basename $d)"; done)
[ -n "$pk" ] && (cd $PRIN && nice -n 5 /usr/local/anaconda3/2024.02/bin/python -u tools/import_all_when_free.py $pk)
COMMON="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages"
./run_steps.sh princeton oar $COMMON >> logs/steps-princeton.log 2>&1 < /dev/null &
./run_steps.sh cmu $COMMON >> logs/steps-cmu.log 2>&1 < /dev/null &
./run_steps.sh epfl $COMMON infoscience >> logs/steps-epfl.log 2>&1 < /dev/null &
./run_steps.sh mit $COMMON dspace >> logs/steps-mit.log 2>&1 < /dev/null &
./run_steps.sh berkeley $COMMON techrpt pubpages >> logs/steps-berkeley.log 2>&1 < /dev/null &
./run_steps.sh stanford $COMMON >> logs/steps-stanford.log 2>&1 < /dev/null &
wait
pk=$(ls -d $OUT/discovery/claude-labpapers-*-2026102[9]*/ $OUT/discovery/claude-labpapers-*-2026103*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (cd $PRIN && nice -n 5 /usr/local/anaconda3/2024.02/bin/python -u tools/import_all_when_free.py $pk)
echo '{"addworks_1029": "done"}'
