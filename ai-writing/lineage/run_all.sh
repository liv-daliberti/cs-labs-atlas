#!/bin/bash
# One command for the lineage study on any link snapshot / paper set / detector table:
#   LINEAGE_HIER=<snapshot or live hierarchy> LINEAGE_TAG=<id> [LINEAGE_AI=<detector parquet>] ai-writing/lineage/run_all.sh
# build (login node, 12 s) -> 13 CPU array tasks -> report. Waits with tools/slurm_wait.py (one sacct call per >= 120 s).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$HERE"
$CS_ATLAS_ENV_PY lineage_build.py
JOB=$(sbatch --parsable --array=0-12%6 lineage.slurm)
$CS_ATLAS_ENV_PY "$HERE/../../tools/slurm_wait.py" "$JOB"
$CS_ATLAS_ENV_PY lineage_report.py
