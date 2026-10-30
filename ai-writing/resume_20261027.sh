#!/bin/bash
# Resume refresh_20261027.sh after the detector publish (its gate check misread a passed gate: grep -q closed the pipe).
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py)
PY=${CS_ATLAS_ENV_PY}
export LD_LIBRARY_PATH="${CS_ATLAS_ENV_LIB}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
say() { echo "{\"at\": \"$(date -u +%FT%TZ)\", $1}"; }
cd ${CS_ATLAS_AI_WRITING}/diversity
step() { nice -n 10 "$PY" -u "$@"; }
for round in $(seq 1 12); do
  while [ "$(squeue -u "$USER" -h -n aiw-divemb -o %i | wc -l)" -ge 1 ]; do sleep 300; done
  step embed_fulltext.py merge; step embed_fulltext.py export
  todo=$(step embed_fulltext.py status --todo-jobs 2>/dev/null | tail -1)
  say "\"embed_round\": $round, \"todo_jobs\": \"$todo\""
  [ "${todo:-0}" = 0 ] && break
  ./submit_embed.sh
done
[ "${todo:-0}" = 0 ] || { say '"stopped": "embeddings still have todo"'; exit 1; }
say '"step": "vectors"'
AIW_AI_SOURCE=paragraph JOBS=16 ./run_all.sh --local --no-submit
say '"done": "battery"'
