#!/bin/bash
# One command for the writing-style study: STYLE_TAG=<id> [STYLE_AI=...] [STYLE_FULLTEXT_DB=<texts db with the main body>] ai-writing/style/run_all.sh
# extract (abstract, allai, fulltext) -> analyze (abstract, fulltext) -> report. Waits with tools/slurm_wait.py.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/../../paths.sh"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$HERE"
J1=$(sbatch --parsable style.slurm extract abstract); J2=$(sbatch --parsable style.slurm extract allai); J3=$(sbatch --parsable style.slurm extract fulltext)
A1=$(sbatch --parsable --dependency=afterok:$J1:$J2 style.slurm analyze abstract); A2=$(sbatch --parsable --dependency=afterok:$J3 style.slurm analyze fulltext)
$CS_ATLAS_ENV_PY "$HERE/../../tools/slurm_wait.py" "$A1" "$A2"
$CS_ATLAS_ENV_PY style_report.py
