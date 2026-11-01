#!/bin/bash
#SBATCH --job-name=channels-1030
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/channels-1030-%j.out
# 2026-10-30 channels for every school, one after another (run_steps.sh's per-channel locks): CHANNELS (default
# arxiv_loose: preprints under another title, validated on a hand-checked sample; ledger_found: the ledger's new open
# copies). Princeton's packages are imported through its own import path afterwards, as in newsteps.slurm.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1  # submit from the code root
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FTP_PY="$CS_ATLAS_PY"  # the pinned project env (2026-10-31)
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in ${SCHOOLS:-mit berkeley stanford princeton epfl cmu}; do
  ./run_steps.sh $s ${CHANNELS:-arxiv_loose} >> "$CS_ATLAS_FT_LOGS"/steps-$s.log 2>&1 < /dev/null
done
PRIN=$(cs_atlas_sweep claude-princeton-20261015)
OUT=$CS_ATLAS_STORES/princeton
pk=$(ls -d $OUT/discovery/claude-labpapers-{arxiv_loose,ledger_found,oa_publisher}-*/ 2>/dev/null | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (cd $PRIN && nice -n 5 $FTP_PY -u tools/import_all_when_free.py $pk)
echo '{"channels-1030": "done"}'
