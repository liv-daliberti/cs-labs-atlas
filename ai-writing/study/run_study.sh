#!/bin/bash
# One command for the 12-school pre/post-ChatGPT study: ai-writing/study/run_study.sh [SNAPSHOT_ID] [MODE] [BASE]
#   (no mode)        analyse the sealed snapshot SNAPSHOT_ID
#   snapshot         rebuild + seal SNAPSHOT_ID from releases/latest first (no scoring of new papers)
#   hetero           heterogeneity layer on the analysed snapshot (needs study_prep.py output): PI career ages (OpenAlex, ~2,500 credits) -> group attributes -> splits -> figures + HETEROGENEITY.md
#   sameness         non-text sameness measures (sameness_*.py) on the prepared tables of SNAPSHOT_ID (study_prep.py must have run): reference overlap, citation concentration,
#                    benchmark/method clustering, topic concentration -> results/<id>/sameness/SAMENESS.md. All jobs <= 59 min, afterok chain.
#   delta BASE       score and embed what the earlier build and snapshot BASE never covered, then build + seal SNAPSHOT_ID with that delta, then analyse:
#                    list -> sections (4 shards) + texts -> GPU: abstract embeddings (7 models), v1 abstract flag, detector v3 passages -> per-paper table
#                    -> snapshot build --delta-base BASE -> OpenAlex leftovers -> seal -> prep -> layers -> figures -> report (compared with BASE) -> ai_share.json
#   field300 [STAGE]  the field-300 abstract-level extension (owner 2026-11-08; ID field300-2026-11-08): all 300 GRAS 2025 CS&E universities, 2016-2025 computer-science papers from the OpenAlex bulk snapshot.
#                    STAGE corpus (default): stream the snapshot (array of 95 chunks) -> merge + counts -> prep (tables + GPU text store). STAGE gpu: detector + two embedding models (arrays of F300_NSH shards,
#                    one A5000 each, restartable; resubmit to resume). STAGE analyze: ai | topics | embeds | sameness (overlap, concentration, bench) -> hetero -> report. STAGE seal: snapshot build + seal.
#   designs          the three design layers on the sealed snapshot SNAPSHOT_ID (needs its prep output, results/<id>/work/panel.parquet; owner 2026-11-08):
#                    OpenAlex affiliation scan (array) -> design prep (PI tables, exposures) -> PI panel with author fixed effects | exposure DiD + event studies
#                    | arXiv-revision pairs -> CPU fetch + main/appendix split of the versions (array of 24) -> GPU scoring (array of 6, one A5000 each, restartable by chunk) -> revision analysis -> design figures + DESIGNS tables
# Every step is a Slurm job (<= 59 min, explicit cpus/mem/gres) chained with afterok; restartable (each stage skips finished output). Waiting: tools/slurm_wait.py <ids>.
set -euo pipefail
ID=${1:-2026-11-07}; MODE=${2:-}; BASE=${3:-}
HERE=$(cd "$(dirname "$0")" && pwd)
export STUDY_CODE=$HERE
if [ "$MODE" = field300 ]; then
  ST=${BASE:-corpus}; ID=field300-2026-11-08; X="--export=ALL,STUDY_CODE=$HERE"; NSH=${F300_NSH:-24}; MODELS=${F300_MODELS:-specter2_proximity scincl}
  case "$ST" in
  corpus)
    c=$(sbatch --parsable --array=0-94%30 $X --cpus-per-task=1 --mem=6G --time=00:59:00 --job-name=f300-corpus $HERE/study.slurm field300_corpus.py chunk)
    m=$(sbatch --parsable --dependency=afterok:$c $X --cpus-per-task=2 --mem=48G --time=00:59:00 --job-name=f300-merge $HERE/study.slurm field300_corpus.py merge)
    p=$(sbatch --parsable --dependency=afterok:$m $X --cpus-per-task=4 --mem=64G --time=00:59:00 --job-name=f300-prep $HERE/study.slurm field300_prep.py build)
    echo "field300 corpus chain: chunks $c merge $m prep $p" ;;
  gpu)
    d=$(sbatch --parsable --array=0-$((NSH-1)) $X,F300_NSH=$NSH --job-name=f300-detect $HERE/field300_gpu.slurm detect)
    echo "field300 gpu: detect $d"
    for M in $MODELS; do e=$(sbatch --parsable --array=0-$((NSH-1)) $X,F300_NSH=$NSH --job-name=f300-emb-$M $HERE/field300_gpu.slurm embed $M); echo "  embed $M $e"; done ;;
  analyze)
    A="sbatch --parsable $X --cpus-per-task=8"
    a=$($A --mem=32G --time=00:30:00 --job-name=f300-ai $HERE/study.slurm field300_analyze.py ai)
    t=$($A --mem=32G --time=00:59:00 --job-name=f300-topics $HERE/study.slurm field300_analyze.py topics)
    es=(); for M in $MODELS; do es+=($($A --mem=64G --time=00:59:00 --job-name=f300-emb-an $HERE/study.slurm field300_analyze.py embed --model $M)); done
    sp=$($A --mem=64G --time=00:59:00 --job-name=f300-sprep $HERE/study.slurm field300_sameness.py prep)
    jobs=()
    for S in journal refs10; do
      jobs+=($(sbatch --parsable --dependency=afterok:$sp $X --cpus-per-task=4 --mem=64G --time=00:59:00 --job-name=f300-ovl $HERE/study.slurm field300_sameness.py overlap --sample $S --groups ALL,tier,english,region,size))
      jobs+=($(sbatch --parsable --dependency=afterok:$sp $X --cpus-per-task=4 --mem=64G --time=00:59:00 --job-name=f300-conc $HERE/study.slurm field300_sameness.py concentration --sample $S --groups ALL,tier,english))
    done
    jobs+=($(sbatch --parsable --dependency=afterok:$sp $X --cpus-per-task=4 --mem=32G --time=00:59:00 --job-name=f300-bench $HERE/study.slurm field300_sameness.py bench --groups ALL,tier,english))
    dep=$(IFS=:; echo "$a:$t:${es[*]// /:}" | tr ' ' ':')
    h=$(sbatch --parsable --dependency=afterok:$dep $X --cpus-per-task=4 --mem=24G --time=00:30:00 --job-name=f300-hetero $HERE/study.slurm field300_hetero.py run --models ${MODELS// /,})
    alld=$(IFS=:; echo "$h:${jobs[*]}" | tr ' ' ':')
    sbatch --parsable --dependency=afterok:$alld $X --cpus-per-task=2 --mem=16G --time=00:30:00 --job-name=f300-report $HERE/study.slurm field300_report.py --models ${MODELS// /,} >/dev/null
    echo "field300 analyze: ai $a topics $t embed ${es[*]} sameness-prep $sp sameness ${jobs[*]} hetero $h" ;;
  seal)
    b=$(sbatch --parsable $X --cpus-per-task=4 --mem=48G --time=00:59:00 --job-name=f300-snap $HERE/study.slurm field300_snapshot.py build --models ${MODELS// /,})
    sbatch --parsable --dependency=afterok:$b $X --cpus-per-task=4 --mem=8G --time=00:59:00 --job-name=f300-seal $HERE/study.slurm field300_snapshot.py seal >/dev/null
    echo "field300 seal: build $b" ;;
  *) echo "field300 STAGE: corpus | gpu | analyze | seal"; exit 2 ;;
  esac
  exit 0
fi
if [ "$MODE" = sameness ]; then
  S="sbatch --parsable --exclude=node302,node014 --export=ALL,STUDY_CODE=$HERE $HERE/study.slurm"
  a=$($S --cpus-per-task=2 --mem=8G --time=00:20:00 sameness_bench.py abstract --id "$ID")
  f=$($S --cpus-per-task=16 --mem=6G --time=00:30:00 sameness_bench.py fulltext --id "$ID" -j 15)
  o1=$($S --cpus-per-task=8 --mem=4G --time=00:20:00 sameness_refs.py overlap --sample refs10 --id "$ID")
  o2=$($S --cpus-per-task=8 --mem=4G --time=00:20:00 sameness_refs.py overlap --sample journal --id "$ID")
  c1=$($S --cpus-per-task=4 --mem=4G --time=00:59:00 sameness_refs.py concentration --sample refs10 --id "$ID")
  c2=$($S --cpus-per-task=4 --mem=4G --time=00:59:00 sameness_refs.py concentration --sample journal --id "$ID")
  t=$($S --cpus-per-task=4 --mem=4G --time=00:30:00 sameness_topics.py run --id "$ID")
  b=$(sbatch --parsable --dependency=afterok:$a:$f --exclude=node302,node014 --export=ALL,STUDY_CODE=$HERE --cpus-per-task=4 --mem=8G --time=00:30:00 $HERE/study.slurm sameness_bench.py analyze --id "$ID")
  h=$(sbatch --parsable --dependency=afterok:$a --exclude=node302,node014 --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G --time=00:10:00 $HERE/study.slurm sameness_bench.py handcheck --id "$ID")
  r=$(sbatch --parsable --dependency=afterok:$b:$h:$o1:$o2:$c1:$c2:$t --exclude=node302,node014 --export=ALL,STUDY_CODE=$HERE --cpus-per-task=2 --mem=8G --time=00:20:00 $HERE/study.slurm sameness_report.py --id "$ID")
  echo "sameness chain: abstract $a fulltext $f overlap $o1 $o2 concentration $c1 $c2 topics $t bench $b handcheck $h report $r"
  exit 0
fi
CPU="sbatch --parsable --export=ALL,STUDY_CODE=$HERE $HERE/study.slurm"
GPU="sbatch --parsable --export=ALL,STUDY_CODE=$HERE,DELTA_BASE=${BASE:-$ID} $HERE/study_delta_gpu.slurm"
dep=""
if [ "$MODE" = hetero ]; then      # results/<ID>/heterogeneity/: study_hetero_authors.py (network, restartable) -> attr -> analysis -> report
  X="--export=ALL,STUDY_CODE=$HERE"
  h1=$(sbatch --parsable $X --cpus-per-task=1 --mem=1G --time=00:59:00 $HERE/study.slurm study_hetero_authors.py --id "$ID")
  h2=$(sbatch --parsable --dependency=afterok:$h1 $X --cpus-per-task=2 --mem=4G --time=00:20:00 $HERE/study.slurm study_hetero_attr.py --id "$ID")
  h3=$(sbatch --parsable --dependency=afterok:$h2 $X --cpus-per-task=4 --mem=8G --time=00:30:00 $HERE/study.slurm study_hetero.py --id "$ID")
  h4=$(sbatch --parsable --dependency=afterok:$h3 $X --cpus-per-task=2 --mem=8G --time=00:20:00 $HERE/study.slurm study_hetero_report.py --id "$ID")
  echo "hetero chain: career $h1 attr $h2 analysis $h3 report $h4"; exit 0
fi
if [ "$MODE" = designs ]; then
  X="--export=ALL,STUDY_CODE=$HERE,SNAPSHOT_ID=$ID"; NSH=6
  n=16   # = len(study_design_prep.tasks()) (OpenAlex stores x row ranges); tests/test_study_designs.py checks that the two agree
  o=$(sbatch --parsable --array=0-$((n-1)) $X --cpus-per-task=2 --mem=8G --time=00:59:00 --job-name=sd-oascan $HERE/study.slurm study_design_prep.py oa-scan --id "$ID")
  b=$(sbatch --parsable --dependency=afterok:$o $X --cpus-per-task=4 --mem=32G --time=00:45:00 --job-name=sd-prep $HERE/study.slurm study_design_prep.py build --id "$ID")
  l=$(sbatch --parsable $X --cpus-per-task=2 --mem=8G --time=00:20:00 --job-name=sd-revlist $HERE/study.slurm study_design_revision.py list --id "$ID")
  NF=24   # fetch tasks: PDFs from the public cloud mirror (storage.googleapis.com), split into main / appendix, nothing kept but the text
  fe=$(sbatch --parsable --array=0-$((NF-1)) --dependency=afterok:$l $X --cpus-per-task=6 --mem=8G --time=00:59:00 --job-name=sd-revfetch $HERE/study.slurm study_design_revision_fetch.py --id "$ID" --of $NF)
  g=$(sbatch --parsable --array=0-$((NSH-1)) --dependency=afterok:$fe $X $HERE/study_design_revision_gpu.slurm $NSH)
  p=$(sbatch --parsable --dependency=afterok:$b $X --cpus-per-task=4 --mem=16G --time=00:30:00 --job-name=sd-panel $HERE/study.slurm study_design_panel.py --id "$ID")
  e=$(sbatch --parsable --dependency=afterok:$b $X --cpus-per-task=4 --mem=24G --time=00:45:00 --job-name=sd-expo $HERE/study.slurm study_design_exposure.py --id "$ID")
  r=$(sbatch --parsable --dependency=afterok:$b:$g $X --cpus-per-task=4 --mem=16G --time=00:45:00 --job-name=sd-revan $HERE/study.slurm study_design_revision.py analyze --id "$ID")
  f=$(sbatch --parsable --dependency=afterok:$p:$e:$r $X --cpus-per-task=2 --mem=8G --time=00:20:00 --job-name=sd-fig $HERE/study.slurm study_design_figures.py --id "$ID")
  sbatch --parsable --dependency=afterok:$f $X --cpus-per-task=2 --mem=4G --time=00:10:00 --job-name=sd-report $HERE/study.slurm study_design_report.py --id "$ID" >/dev/null
  echo "designs chain: oa-scan $o prep $b revlist $l fetch $fe gpu $g panel $p exposure $e revision $r figures $f"; exit 0
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
