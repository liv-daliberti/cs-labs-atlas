#!/bin/bash
# One command for the 12-school pre/post-ChatGPT study on a snapshot: ai-writing/study/run_study.sh [SNAPSHOT_ID] [snapshot]
#   snapshot  also (re)build and seal the snapshot from releases/latest first (otherwise the sealed snapshot is used)
# Every step is a Slurm job (<= 59 min, explicit cpus/mem) chained with afterok; the analysis layers run in parallel after prep.
# Restartable: re-running overwrites the results of the same snapshot id only. Waiting: tools/slurm_wait.py <ids>.
set -euo pipefail
ID=${1:-2026-11-07}; MODE=${2:-}
HERE=$(cd "$(dirname "$0")" && pwd)
S="sbatch --parsable $HERE/study.slurm"
dep=""
if [ "$MODE" = snapshot ]; then
  j=$($S study_snapshot.py build --id "$ID"); j=$(sbatch --parsable --dependency=afterok:$j --cpus-per-task=2 --mem=8G $HERE/study.slurm study_delta_oa.py --id "$ID" --cap 400)
  j=$(sbatch --parsable --dependency=afterok:$j --cpus-per-task=4 --mem=16G $HERE/study.slurm study_snapshot.py seal --id "$ID" -j 4); dep="--dependency=afterok:$j"
fi
p=$(sbatch --parsable $dep --cpus-per-task=4 --mem=24G $HERE/study.slurm study_prep.py --id "$ID")
ids=()
for l in ai topics citation; do ids+=($(sbatch --parsable --dependency=afterok:$p --cpus-per-task=8 --mem=32G $HERE/study.slurm study_analyze.py $l --id "$ID")); done
ids+=($(sbatch --parsable --dependency=afterok:$p --cpus-per-task=8 --mem=48G $HERE/study.slurm study_analyze.py embed --id "$ID"))
ids+=($(sbatch --parsable --dependency=afterok:$p --cpus-per-task=16 --mem=48G $HERE/study.slurm study_analyze.py event --id "$ID"))
all=$(IFS=:; echo "${ids[*]}")
f=$(sbatch --parsable --dependency=afterok:$all --cpus-per-task=2 --mem=8G $HERE/study.slurm study_figures.py --id "$ID")
r=$(sbatch --parsable --dependency=afterok:$f --cpus-per-task=2 --mem=8G $HERE/study.slurm study_report.py --id "$ID")
sbatch --parsable --dependency=afterok:$r --cpus-per-task=2 --mem=8G $HERE/study.slurm study_ai_share.py --id "$ID" >/dev/null
echo "chain: prep $p, layers ${ids[*]}, figures $f, report $r"
