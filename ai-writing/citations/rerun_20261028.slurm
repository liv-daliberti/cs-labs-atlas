#!/bin/bash
# The citation analysis rerun with Stanford in (2026-10-28), in the documented order: tables, coverage, pooled measures
# and within-lab fits on both sources, distribution by year, q2 (v1 abstract scores of cited works) and q2v2 (passage
# detector sample), figures, cited years by AI; then fields/ai_by_field.py (it reads the same OpenAlex cache).
# Run after fetch_new.slurm (citing + works + S2) and the v1 score phase 'c' (score.py prep c; score.slurm c N).
#SBATCH --job-name=cit-rerun
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/citations/logs/rerun-%j.out
set -uo pipefail
export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export TMPDIR=/tmp/cit-rerun-$SLURM_JOB_ID SQLITE_TMPDIR=/tmp/cit-rerun-$SLURM_JOB_ID; mkdir -p $TMPDIR; trap 'rm -rf "$TMPDIR"' EXIT
cd /n/fs/resemble/cs-atlas/work/ai-writing/citations
PY="nice -n 10 /n/fs/resemble/cs-atlas-env/py310/bin/python -u -B"
step() { echo "== $* ($(date +%T))"; $PY "$@" || { echo "FAILED: $*"; exit 1; }; }
step build.py
step coverage.py
step analyze.py --source oa --procs 24
step analyze.py --source s2 --procs 24
step within.py --source oa
step within.py --source s2
step dist_by_year.py --source oa
step dist_by_year.py --source s2
step q2.py
step q2v2.py
step figures.py recent  # panel A as published 10-28: share of references <= 2 years old
step cited_years_by_ai.py
cd ../fields && step ai_by_field.py
echo ALLDONE
