#!/bin/bash
#SBATCH --job-name=bulk-oa-channels
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=24:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/bulk-oa-channels-%j.out
# 2026-11-04 the bulk open-access channels (docs/CHANNELS.md), for each school one after another:
#   CHANNELS  (default oa_locations arxiv_bulk core_bulk s2_bulk)   SCHOOLS  (default the 7 released schools plus uchicago gatech)   DRY=1 for --dry
# A catalog backup (catalog_lock.backup_catalog, sqlite online backup under the write lock) is taken before every channel's write; Princeton's
# candidates go to a discovery package (its own import path), so its 2 GB catalog is not touched. Submit with `atlas submit`.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
[ -f "$CS_ATLAS_FT_RAW/bulk-oa/targets.jsonl.gz" ] || { echo "no targets table: run bulk-oa-targets.slurm first" >&2; exit 1; }
for s in ${SCHOOLS:-princeton cmu epfl mit berkeley stanford michigan uchicago gatech}; do
  for ch in ${CHANNELS:-oa_locations arxiv_bulk core_bulk s2_bulk}; do
    if [ -z "$DRY" ] && [ "$s" != princeton ]; then
      $CS_ATLAS_PY -I -c "
import sys; sys.path.insert(0, '$CS_ATLAS_FULLTEXT_PUSH')
import ftp_common as F
print('backup', F.backup_catalog(F.FT / '$s', 'before-bulk-oa-$ch', keep=8))" || { echo "backup failed for $s $ch: skipped" >&2; continue; }
    fi
    (
      flock 9
      echo "{\"at\": \"$(date -u +%FT%TZ)\", \"start\": \"$s $ch\"}"
      nice -n 5 $CS_ATLAS_PY -I -u channel_runner.py $s $ch ${DRY:+--dry} || echo "{\"failed\": \"$s $ch\"}"
    ) 9>>"$CS_ATLAS_FT_LOGS"/run_steps-$ch.lock
  done
done
echo '{"bulk-oa-channels": "done"}'
