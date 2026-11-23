#!/bin/bash
# Launch / top up the full run: submits shards that are neither complete (meta complete=1) nor already queued (job name sum14b / sum14b-<i>).
#   SUM_PART=all SUM_ACCT=mltheory SUM_TIME=00:59:00 SUM_MAX=12 [SUM_MODEL=... SUM_KV=fp8] sum_submit.sh
set -euo pipefail
cd "$(dirname "$0")"
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-${SUM_ID:-20261123}
rm -f $W/STOP
queued=$(squeue -r -u "$USER" -h -o "%j %K" | awk '$1=="sum14b"{print $2} $1~/^sum14b-/{sub("sum14b-","",$1); print $1}')
need=()
for i in $(seq 0 63); do
  f=$W/shards/sum-$i.sqlite
  [ -f "$f" ] && [ "$(sqlite3 -readonly "$f" "select value from meta where key='complete'" 2>/dev/null)" = 1 ] && continue
  grep -qx "$i" <<<"$queued" && continue
  need+=($i)
done
[ ${#need[@]} -gt 0 ] || { echo "nothing to submit"; exit 0; }
arr=$(IFS=,; echo "${need[*]}")
sbatch --parsable --partition=${SUM_PART:-all} --account=${SUM_ACCT:-mltheory} --time=${SUM_TIME:-00:59:00} --array=$arr%${SUM_MAX:-12} \
  --export=ALL,SUM_TIME=${SUM_TIME:-00:59:00} sum_full.slurm
echo "submitted ${#need[@]} shards: $arr"
