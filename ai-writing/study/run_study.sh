#!/bin/bash
# One command for the 12-school pre/post-ChatGPT study: ai-writing/study/run_study.sh [SNAPSHOT_ID] [MODE] [BASE]
#   (no mode)        analyse the sealed snapshot SNAPSHOT_ID
#   snapshot         rebuild + seal SNAPSHOT_ID from releases/latest first (no scoring of new papers)
#   hetero           heterogeneity layer on the analysed snapshot (needs study_prep.py output): PI career ages (OpenAlex, ~2,500 credits) -> group attributes -> splits -> figures + HETEROGENEITY.md
#   delta BASE       score and embed what the earlier build and snapshot BASE never covered, then build + seal SNAPSHOT_ID with that delta, then analyse:
#                    list -> sections (4 shards) + texts -> GPU: abstract embeddings (7 models), v1 abstract flag, detector v3 passages -> per-paper table
#                    -> snapshot build --delta-base BASE -> OpenAlex leftovers -> seal -> prep -> layers -> figures -> report (compared with BASE) -> ai_share.json
# Every step is a Slurm job (<= 59 min, explicit cpus/mem/gres) chained with afterok; restartable (each stage skips finished output). Waiting: tools/slurm_wait.py <ids>.
set -euo pipefail
ID=${1:-2026-11-07}; MODE=${2:-}; BASE=${3:-}
HERE=$(cd "$(dirname "$0")" && pwd)
export STUDY_CODE=$HERE
CPU="sbatch --parsable --export=ALL,STUDY_CODE=$HERE $HERE/study.slurm"
GPU="sbatch --parsable --export=ALL,STUDY_CODE=$HERE,DELTA_BASE=${BASE:-$ID} $HERE/study_delta_gpu.slurm"
dep=""
if [ "$MODE" = hetero ]; then      # results/<ID>/heterogeneity/: study_hetero_authors.py (network, restartable) -> attr -> analysis -> report
  X="--export=ALL,STUDY_CODE=$HERE"
  h1=$(sbatch --parsable $X --cpus-per-task=1 --mem=2G --time=00:59:00 $HERE/study.slurm study_hetero_authors.py --id "$ID")
  h2=$(sbatch --parsable --dependency=afterok:$h1 $X --cpus-per-task=2 --mem=16G --time=00:30:00 $HERE/study.slurm study_hetero_attr.py --id "$ID")
  h3=$(sbatch --parsable --dependency=afterok:$h2 $X --cpus-per-task=8 --mem=@HETERO_MEM@ --time=00:59:00 $HERE/study.slurm study_hetero.py --id "$ID")
  h4=$(sbatch --parsable --dependency=afterok:$h3 $X --cpus-per-task=2 --mem=8G --time=00:20:00 $HERE/study.slurm study_hetero_report.py --id "$ID")
  echo "hetero chain: career $h1 attr $h2 analysis $h3 report $h4"; exit 0
fi
if [ "$MODE" = delta ]; then
  [ -n "$BASE" ] || { echo "delta needs BASE (the sealed snapshot whose membership and universe define the delta)"; exit 2; }
  l=$($CPU --cpus-per-task=4 --mem=24G --time=00:45:00 study_delta_build.py list --id "$BASE")
  t=$(sbatch --parsable --dependency=afterok:$l --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G --time=00:20:00 $HERE/study.slurm study_delta_build.py texts --id "$BASE")
  secs=()
  for i in 0 1 2 3; do secs+=($(sbatch --parsable --dependency=afterok:$l --export=ALL,STUDY_CODE=$HERE --cpus-per-task=8 --mem=24G --time=00:59:00 $HERE/study.slurm study_delta_build.py sections --id "$BASE" --shard $i --nshards 4 -j 8)); done
  sj=$(IFS=:; echo "${secs[*]}")
  e=$(sbatch --parsable --dependency=afterok:$t --export=ALL,STUDY_CODE=$HERE,DELTA_BASE=$BASE $HERE/study_delta_gpu.slurm embed)
  a=$(sbatch --parsable --dependency=afterok:$t --export=ALL,STUDY_CODE=$HERE,DELTA_BASE=$BASE $HERE/study_delta_gpu.slurm abstract)
  s=$(sbatch --parsable --dependency=afterok:$sj --export=ALL,STUDY_CODE=$HERE,DELTA_BASE=$BASE $HERE/study_delta_gpu.slurm score)
  p=$(sbatch --parsable --dependency=afterok:$e:$a:$s --export=ALL,STUDY_CODE=$HERE --cpus-per-task=4 --mem=16G --time=00:30:00 $HERE/study.slurm study_delta_build.py paper --id "$BASE")
  b=$(sbatch --parsable --dependency=afterok:$p --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G $HERE/study.slurm study_snapshot.py build --id "$ID" --delta-base "$BASE")
  o=$(sbatch --parsable --dependency=afterok:$b --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G $HERE/study.slurm study_delta_oa.py --id "$ID" --cap 400)
  z=$(sbatch --parsable --dependency=afterok:$o --export=ALL,STUDY_CODE=$HERE --cpus-per-task=4 --mem=16G $HERE/study.slurm study_snapshot.py seal --id "$ID" -j 4)
  dep="--dependency=afterok:$z"; echo "delta chain: list $l texts $t sections $sj gpu $e $a $s paper $p build $b oa $o seal $z"
elif [ "$MODE" = snapshot ]; then
  j=$($CPU study_snapshot.py build --id "$ID"); j=$(sbatch --parsable --dependency=afterok:$j --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G $HERE/study.slurm study_delta_oa.py --id "$ID" --cap 400)
  j=$(sbatch --parsable --dependency=afterok:$j --export=ALL,STUDY_CODE=$HERE --cpus-per-task=4 --mem=16G $HERE/study.slurm study_snapshot.py seal --id "$ID" -j 4); dep="--dependency=afterok:$j"
fi
X="--export=ALL,STUDY_CODE=$HERE"
p=$(sbatch --parsable $dep $X --cpus-per-task=4 --mem=24G $HERE/study.slurm study_prep.py --id "$ID")
ids=()
for l in ai topics citation; do ids+=($(sbatch --parsable --dependency=afterok:$p $X --cpus-per-task=8 --mem=32G $HERE/study.slurm study_analyze.py $l --id "$ID")); done
ids+=($(sbatch --parsable --dependency=afterok:$p $X --cpus-per-task=8 --mem=48G $HERE/study.slurm study_analyze.py embed --id "$ID"))
ids+=($(sbatch --parsable --dependency=afterok:$p $X --cpus-per-task=16 --mem=48G $HERE/study.slurm study_analyze.py event --id "$ID"))
all=$(IFS=:; echo "${ids[*]}")
f=$(sbatch --parsable --dependency=afterok:$all $X --cpus-per-task=2 --mem=8G $HERE/study.slurm study_figures.py --id "$ID")
cmp=""; [ -n "$BASE" ] && cmp="--compare $BASE"
r=$(sbatch --parsable --dependency=afterok:$f $X --cpus-per-task=2 --mem=8G $HERE/study.slurm study_report.py --id "$ID" $cmp)
sbatch --parsable --dependency=afterok:$r $X --cpus-per-task=2 --mem=8G $HERE/study.slurm study_ai_share.py --id "$ID" >/dev/null
echo "chain: prep $p, layers ${ids[*]}, figures $f, report $r"
