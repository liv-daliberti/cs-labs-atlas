#!/bin/bash
# One command re-runs the lab-level study: topic convergence, lab event study, full-text IPW; every step is a Slurm job (partition all, account mltheory,
# <= 59 min, --exclude node302,node014,node805,node808) chained by afterok dependencies, test-only first, refused on "Preempts:" (submit.sh).
#   ai-writing/labstudy/run_all.sh [stage ...]       stages: frame ipw topics event ipwrerun reports   (default: all, in that order)
# The code runs from the committed HEAD of this checkout (a snapshot), the data from the main checkout. Configure paths in config.json or with
# LABSTUDY_SCORES_DB / LABSTUDY_UNIVERSE_DB / LABSTUDY_PAPER_SET / LABSTUDY_IPW_TABLE / LABSTUDY_OUT (see lcommon.py): the final paper set (after release 20261105i) and
# detector v3 need only these. Waiting: tools/slurm_wait.py <ids> (one sacct call per >= 120 s); never poll squeue.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WT=$(cd "$HERE/../.." && pwd)
SUB=$HERE/submit.sh
export LABSTUDY_REPORT_DIR=${LABSTUDY_REPORT_DIR:-$WT/ai-writing/diversity/reports}
stages=${*:-frame ipw topics event ipwrerun reports}
ex() { SBATCH_EXTRA="$1" "$SUB" "${@:2}" | tail -1; }
dep=""; ids=()
d() { [ -z "$dep" ] && echo "" || echo "--dependency=afterok:$dep"; }
for s in $stages; do
  case $s in
    frame)    j=$(ex "$(d) --time=00:30:00 --mem=24G --cpus-per-task=4" frame.py) ;;
    ipw)      j=$(ex "$(d) --time=00:40:00 --mem=32G --cpus-per-task=16" ipw.py fit) ;;
    topics)   j1=$(ex "$(d) --time=00:59:00 --mem=64G --cpus-per-task=16" topic_convergence.py run -j 12)
              j2=$(ex "$(d) --time=00:59:00 --mem=64G --cpus-per-task=16" topic_convergence.py run --levels bt_qwen3_0p6b,bt_specter2_proximity --variants none --control -j 12)
              j3=$(ex "$(d) --time=00:59:00 --mem=48G --cpus-per-task=8" event_study.py control)
              j=$j1:$j2:$j3 ;;
    event)    j0=$(ex "$(d) --time=00:20:00 --mem=16G --cpus-per-task=4" event_study.py adoption)
              j=$(ex "--dependency=afterok:$j0${dep:+:$dep} --time=00:59:00 --mem=32G --cpus-per-task=16" event_study.py run -j 14) ;;
    ipwrerun) j=$(ex "$(d) --time=00:59:00 --mem=64G --cpus-per-task=16" ipw_rerun.py all -j 14) ;;
    reports)  j1=$(ex "$(d) --time=00:15:00 --mem=16G --cpus-per-task=2" topic_convergence.py report)
              j2=$(ex "$(d) --time=00:15:00 --mem=16G --cpus-per-task=2" event_study.py report)
              j3=$(ex "$(d) --time=00:15:00 --mem=16G --cpus-per-task=2" ipw_report.py)
              j=$j1:$j2:$j3 ;;
    *) echo "unknown stage $s"; exit 2 ;;
  esac
  echo "stage $s -> job(s) $j"
  dep=$j
done
