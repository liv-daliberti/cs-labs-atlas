#!/bin/bash
# The bootstrap in PARTS: <parts> jobs of ALLAI_BOOT replicates each per model (part 0 also does the point estimates and the lab tables), then `combine`.
#   submit_geom.sh <style> <parts> <model> [<model> ...]      env: ALLAI_BOOT (replicates per part, default 60), ALLAI_RESTRICT, ALLAI_UNFILTERED
set -euo pipefail
cd "$(dirname "$0")/../.."
style=$1; parts=$2; shift 2
for m in "$@"; do
  ids=""
  for ((k = 0; k < parts; k++)); do
    j=$(ALLAI_PART=$k ALLAI_BOOT=${ALLAI_BOOT:-60} bin/atlas submit --from-worktree --parsable ai-writing/allai/analyze.slurm geom "$m" "$style" 2>/dev/null | tail -1)
    ids="$ids:$j"
  done
  c=$(bin/atlas submit --from-worktree --parsable --dependency=afterok$ids ai-writing/allai/analyze.slurm combine "$m" "$style" 2>/dev/null | tail -1)
  echo "{\"model\": \"$m\", \"style\": \"$style\", \"parts\": \"${ids#:}\", \"combine\": \"$c\"}"
done
