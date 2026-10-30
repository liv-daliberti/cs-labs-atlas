#!/bin/bash
# Refresh the AI-writing study to the current hierarchy (owner 2026-10-27: more flagged / not-flagged papers for Figure 3).
#   backup   the outputs this overwrites -> logs/backup-before-refresh-20261027/
#   corpus   build_corpus.py fetch (OpenAlex abstracts of the new lab papers) + build
#   texts    fulltext.py: match the new papers to stored copies, extract
#   detector every stored full text rescored (12-shard A5000 array, the 10-22 request), then merge.py --publish (held-out gate)
#   vectors  full-text SPECTER2 embeddings in rounds of submit_embed.sh (<= 2 jobs queued) until the todo is empty
#   battery  run_all.sh --local --no-submit (paper features, lab diversity, analyses, figures, REPORT.md) on this host
# Log: logs/refresh-20261027.log; the last line is {"done": ...} or {"stopped": ...}.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
AW=${CS_ATLAS_AI_WRITING}
PY=${CS_ATLAS_ENV_PY}
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
say() { echo "{\"at\": \"$(date -u +%FT%TZ)\", $1}"; }
stop() { say "\"stopped\": \"$1\""; exit 1; }
cd "$AW"

B=$AW/logs/backup-before-refresh-20261027
if [ ! -d "$B" ]; then
  mkdir -p "$B/diversity"
  cp -p papers.jsonl.gz paragraph_scores.jsonl.gz detector_v2/paper_ai_fulltext.jsonl.gz "$B/"
  cp -rp diversity/results diversity/figures diversity/REPORT.md diversity/data/paper_features.parquet "$B/diversity/"
fi
say '"step": "backup"'

( set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a; nice python3 -u build_corpus.py fetch )
nice python3 -u build_corpus.py build
say '"step": "corpus"'
nice python3 -u fulltext.py -j 16
say '"step": "texts"'

NS=12
jd=$(sbatch --parsable --partition=all --account=allcs --gres=gpu:a5000:1 --cpus-per-task=8 --mem=24G --time=01:30:00 \
       --array=0-$((NS - 1)) detector_v2/detector.slurm score $NS)
say "\"detector_array\": \"$jd\""

cd "$AW/diversity"
step() { nice -n 10 "$PY" -u "$@"; }
step embed_fulltext.py snapshot; step embed_fulltext.py merge; step embed_fulltext.py export
./submit_embed.sh

while [ -n "$(squeue -h -j "$jd" -o %i 2>/dev/null)" ]; do sleep 300; done
bad=$(sacct -j "$jd" -X -n -o State | grep -vc COMPLETED || true)
[ "$bad" -eq 0 ] || stop "detector array $jd: $bad tasks not COMPLETED"
cd "$AW/detector_v2"
nice "$PY" -u merge.py --publish | tee /dev/stderr | grep -q '"gate_passed": true' || stop "detector gate failed; paragraph_scores not published"
say '"step": "detector"'

cd "$AW/diversity"
for round in $(seq 1 12); do
  while [ "$(squeue -u "$USER" -h -n aiw-divemb -o %i | wc -l)" -ge 1 ]; do sleep 300; done
  step embed_fulltext.py merge; step embed_fulltext.py export
  todo=$(step embed_fulltext.py status --todo-jobs 2>/dev/null | tail -1)
  say "\"embed_round\": $round, \"todo_jobs\": \"$todo\""
  [ "${todo:-0}" = 0 ] && break
  ./submit_embed.sh
done
[ "${todo:-0}" = 0 ] || stop "embeddings still have todo after 12 rounds"
say '"step": "vectors"'

AIW_AI_SOURCE=paragraph JOBS=16 ./run_all.sh --local --no-submit
say '"done": "battery"'
