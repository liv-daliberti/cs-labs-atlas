#!/bin/bash
# Princeton: import the lab-channel candidate packages that are not in the catalog yet (packages written since
# 2026-10-26 were stranded: princeton_pass.sh is skipped while raw/downloads_stopped_for_disk exists), through
# Princeton's own import path (claude-princeton-20261015/tools/import_all_when_free.py: waits for a safe phase and the
# free .collector.lock; already-imported packages carry a receipt and are skipped). The running princeton lab_first_loop
# then downloads them. Re-run after new Princeton packages are written.
#SBATCH --job-name=princeton-pkg-import
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=12:00:00
#SBATCH --output=fulltext-push/local-reuse/logs/princeton-import-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
OUT=${CS_ATLAS_STORES}/princeton
pk=$(ls -d $OUT/discovery/claude-labpapers-*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -u "$CS_ATLAS_VENDOR/princeton_tools/import_all_when_free.py" $pk
