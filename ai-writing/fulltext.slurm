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
cd /n/fs/resemble/cs-atlas/work/ai-writing
export LD_LIBRARY_PATH="/n/fs/resemble/cs-atlas-env/py310/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "{\"node\": \"$(hostname)\", \"start\": \"$(date -u +%FT%TZ)\"}"
/n/fs/resemble/cs-atlas-env/py310/bin/python -u fulltext.py -j "${SLURM_CPUS_PER_TASK:-16}"
echo "{\"end\": \"$(date -u +%FT%TZ)\"}"
