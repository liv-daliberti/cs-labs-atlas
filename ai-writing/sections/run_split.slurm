#!/bin/bash
# Main / references / appendix split of every stored copy, one array task per shard (ai-writing/sections/PLAN.md).
# usage: atlas submit --array=0-3 ai-writing/sections/run_split.slurm  (or sbatch; test with --test-only first)
#SBATCH --job-name=aiw-sections
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/sections-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
NSH=${NSHARDS:-4}; I=${SLURM_ARRAY_TASK_ID:-0}
L=/tmp/aiw-sections-${SLURM_JOB_ID:-0}; mkdir -p $L; trap 'rm -rf "$L"' EXIT
cp "$CS_ATLAS_EMBEDDINGS/texts.sqlite" $L/texts.sqlite
cp "$CS_ATLAS_AI_WRITING/fulltext.sqlite" $L/fulltext.sqlite
cd "${SPLIT_CODE:-$CS_ATLAS_AI_WRITING}/sections"
echo "{\"node\": \"$(hostname)\", \"shard\": $I, \"start\": \"$(date -u +%FT%TZ)\"}"
$CS_ATLAS_PY -u run_split.py --texts $L/texts.sqlite --ft $L/fulltext.sqlite --shard $I --nshards $NSH --out "$CS_ATLAS_AI_WRITING/data/sections" -j "${SLURM_CPUS_PER_TASK:-8}"
