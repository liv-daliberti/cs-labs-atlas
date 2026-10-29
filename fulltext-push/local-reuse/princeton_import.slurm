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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse/logs/princeton-import-%j.out
PRIN=/n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015
OUT=/n/fs/resemble/homogenizing-science/data/fulltext/princeton
pk=$(ls -d $OUT/discovery/claude-labpapers-*/ 2>/dev/null | grep -v newworks | while read d; do [ -s "$d/cs-open-copies-candidates.jsonl" ] && echo "cs_open_copies:$(basename $d)"; done)
cd $PRIN && nice -n 5 /usr/local/anaconda3/2024.02/bin/python -u tools/import_all_when_free.py $pk
