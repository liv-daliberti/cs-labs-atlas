#!/bin/bash
# Launch the lanes that have no live job (name sum14b-lane<L>). Each lane resubmits itself until its shards are complete.
#   SUM_LANES=10 [SUM_PART=all SUM_ACCT=mltheory SUM_TIME=00:59:00 SUM_TP=2] sum_submit.sh
set -euo pipefail
cd "$(dirname "$0")"
W=/n/fs/resemble/homogenizing-science/studies/homogenization/work/summaries14b-${SUM_ID:-20261123}
N=${SUM_LANES:-10}; TP=${SUM_TP:-2}
rm -f $W/STOP
live=$(squeue -u "$USER" -h -o "%j" | grep -oE '^sum14b-lane[0-9]+' | sed 's/sum14b-lane//' || true)
for ((l = 0; l < N; l++)); do
  grep -qx "$l" <<<"$live" && { echo "lane $l live"; continue; }
  j=$(sbatch --parsable --partition=${SUM_PART:-all} --account=${SUM_ACCT:-mltheory} --time=${SUM_TIME:-00:59:00} \
      --gres=gpu:a6000:$TP --cpus-per-task=$((4 * TP)) --mem=$((48 * TP))G --job-name=sum14b-lane$l \
      --export=ALL,SUM_LANE=$l,SUM_LANES=$N,SUM_TP=$TP,SUM_GEN=0 sum_full.slurm)
  echo "lane $l -> $j"
done
