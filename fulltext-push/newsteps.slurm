#!/bin/bash
# 2026-10-29 new channels for every school (lab_channels.py steps oa_refresh dblp_ee s2_title oa_editions; per-channel
# flock in run_steps.sh, so schools take turns on each channel), then Princeton's new packages are imported through
# its own import path (import_all_when_free.py). The running lab_first_loop collectors download the candidates.
#SBATCH --job-name=fulltext-newsteps
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=6
#SBATCH --mem=24G
#SBATCH --time=1-00:00:00
#SBATCH --output=fulltext-push/logs/newsteps-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in ${SCHOOLS:-mit berkeley stanford princeton epfl cmu}; do
  ./run_steps.sh $s oa_refresh dblp_ee s2_title oa_editions >> "$CS_ATLAS_FT_LOGS"/steps-$s.log 2>&1 < /dev/null &
  sleep 30
done
wait
OUT=$CS_ATLAS_STORES/princeton
pk=$(ls -d $OUT/discovery/claude-labpapers-{oa_refresh,dblp_ee,s2_title,oa_editions}-*/ 2>/dev/null | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk)
echo '{"newsteps": "done"}'
