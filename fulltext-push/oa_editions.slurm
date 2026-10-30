#!/bin/bash
# oa_editions for every school now (the newsteps chains reach it only after the slow s2_title step); the chains' later
# oa_editions runs then find the title searches cached. Princeton's package is imported through its own import path.
#SBATCH --job-name=fulltext-oa-editions
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=12:00:00
#SBATCH --output=fulltext-push/logs/oa_editions-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in cmu epfl stanford princeton mit berkeley; do
  ./run_steps.sh $s oa_editions >> logs/steps-$s.log 2>&1 < /dev/null
done
OUT=$CS_ATLAS_STORES/princeton
pk=$(ls -d $OUT/discovery/claude-labpapers-oa_editions-2026103*/ 2>/dev/null | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk)
