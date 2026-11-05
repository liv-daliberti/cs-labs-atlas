#!/bin/bash
# 2026-11-04: add_works.py added 217 lab papers no catalog held (Berkeley 49, MIT 94, CMU 20, EPFL 23, Stanford 15, Michigan 16; Princeton 5 as the
# cs_pi_works package claude-labpapers-newworks-202611050040). This imports that package, then runs every open-copy channel for every released school
# so the new works get candidates (run_steps.sh; per-channel locks; each step only touches works without a copy and URLs not yet known). The download
# loops (downloads.slurm) then fetch them. Same shape as addworks-1029.slurm; CORE stays paused (not listed); Michigan never uses Deep Blue.
#SBATCH --job-name=fulltext-addworks
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=6
#SBATCH --mem=28G
#SBATCH --time=2-00:00:00
#SBATCH --output=fulltext-push/logs/addworks-1104-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
PKG=${PKG:-claude-labpapers-newworks-202611050040}
[ -d "$CS_ATLAS_STORES/princeton/discovery/$PKG" ] && nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" "cs_pi_works:$PKG"
COMMON="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages pihomes wayback_acm"
./run_steps.sh princeton oar $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-princeton.log 2>&1 < /dev/null &
./run_steps.sh cmu $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-cmu.log 2>&1 < /dev/null &
./run_steps.sh epfl $COMMON infoscience >> "$CS_ATLAS_FT_LOGS"/steps-epfl.log 2>&1 < /dev/null &
./run_steps.sh mit $COMMON dspace >> "$CS_ATLAS_FT_LOGS"/steps-mit.log 2>&1 < /dev/null &
./run_steps.sh berkeley $COMMON techrpt pubpages >> "$CS_ATLAS_FT_LOGS"/steps-berkeley.log 2>&1 < /dev/null &
./run_steps.sh stanford $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-stanford.log 2>&1 < /dev/null &
./run_steps.sh michigan $COMMON >> "$CS_ATLAS_FT_LOGS"/steps-michigan.log 2>&1 < /dev/null &
wait
echo '{"addworks_1104": "done"}'
