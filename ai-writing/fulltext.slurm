#!/bin/bash
# fulltext.py on a compute node (2026-10-28, Stanford added): match papers.jsonl.gz to the schools' stored copies,
# reuse the homogenization extracts, pdftotext the rest into ai-writing/fulltext.sqlite (new keys only; existing rows kept).
#SBATCH --job-name=aiw-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/n/fs/resemble/cs-atlas/work/ai-writing/logs/fulltext-%j.out
set -euo pipefail
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_AI_WRITING"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
$CS_ATLAS_ENV_PY -u fulltext.py -j "${SLURM_CPUS_PER_TASK:-16}"
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
