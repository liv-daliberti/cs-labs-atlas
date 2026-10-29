#!/bin/bash
# Submit the full-text embedding jobs: nothing if any is already queued or running; otherwise one job, plus a second
# that starts after it (afterany) when the todo needs more than one job at the last measured rate. Never more than 2.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
ROOT=/n/fs/resemble/maxent-grpo
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python
export LD_LIBRARY_PATH="$(dirname "$(readlink -f "$PY")")/../lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$D"
queued=$(squeue -u "$USER" -h -n aiw-divemb -o %i | wc -l)
if [ "$queued" -ge 1 ]; then echo "{\"embed_jobs_in_queue\": $queued, \"submitted\": 0}"; exit 0; fi
jobs=$(nice $PY embed_fulltext.py status --todo-jobs 2>/dev/null | tail -1)
if [ "${jobs:-0}" -eq 0 ]; then echo '{"embed_todo": 0, "submitted": 0}'; exit 0; fi
j1=$(sbatch --parsable embed_fulltext.slurm)
if [ "$jobs" -ge 2 ]; then
  j2=$(sbatch --parsable --dependency=afterany:$j1 embed_fulltext.slurm)
  echo "{\"submitted\": [\"$j1\", \"$j2\"], \"jobs_needed\": $jobs}"
else
  echo "{\"submitted\": [\"$j1\"], \"jobs_needed\": $jobs}"
fi
