#!/bin/bash
#SBATCH --job-name=ft-advisers
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:55:00
#SBATCH --exclude=node302,node014
#SBATCH --output=hierarchy/logs/ft-advisers-%A_%a.log
# Restartable: each shard keeps its own sqlite and skips finished works. usage: SCHOOL=gatech SHARDS=16 sbatch --array=0-15%16 tools/fulltext-advisers.slurm
set -euo pipefail
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh"
OUT="${FT_ADV_OUT:-$CS_ATLAS_ROOT/scratch/fulltext-advisers}"
mkdir -p "$OUT"
"$CS_ATLAS_PY" -I "$CS_ATLAS_TOOLS/fulltext_advisers.py" scan "${SCHOOL:?SCHOOL}" --shard "$SLURM_ARRAY_TASK_ID" --shards "${SHARDS:?SHARDS}" --out "$OUT"
