#!/bin/bash
#SBATCH --job-name=recover-1030
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=16:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/recover-1030-%j.out
# 2026-10-30 recovery from the first unavailability ledger:
#   1. add_works.py: lab papers no catalog work matches (the ledger's found_not_in_catalog: 481) become queued works
#   2. ledger_found: the open copies the ledger's checks found that are not candidates yet (found_awaiting_download)
#   3. the usual channels for the works added in 1 (their candidates), as addworks-1029.slurm did
#   4. Princeton's packages through its own import path
. /n/fs/resemble/homogenizing-science/code/paths.sh
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FTP_PY="$CS_ATLAS_ENV_PY"
PY="nice -n 5 $FTP_PY -I -u"
cd "$CS_ATLAS_FULLTEXT_PUSH"
OUT=$CS_ATLAS_STORES/princeton
PRIN_TOOLS=$(cs_atlas_sweep claude-princeton-20261015)/tools
for s in ${SCHOOLS:-stanford mit berkeley cmu epfl princeton}; do $PY add_works.py $s >> logs/steps-$s.log 2>&1; done
pk=$(ls -d $OUT/discovery/claude-labpapers-newworks-20261030*/ 2>/dev/null | while read d; do echo "cs_pi_works:$(basename $d)"; done)
[ -n "$pk" ] && (cd "$PRIN_TOOLS/.." && nice -n 5 $FTP_PY -u tools/import_all_when_free.py $pk)
for s in ${SCHOOLS:-stanford mit berkeley cmu epfl princeton}; do
  ./run_steps.sh $s ledger_found oa_arxiv openalex proceedings dblp_ee s2 core labpages >> logs/steps-$s.log 2>&1 < /dev/null
done
pk=$(ls -d $OUT/discovery/claude-labpapers-*-20261030*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
[ -n "$pk" ] && (cd "$PRIN_TOOLS/.." && nice -n 5 $FTP_PY -u tools/import_all_when_free.py $pk)
echo '{"recover-1030": "done"}'
