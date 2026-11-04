#!/bin/bash
#SBATCH --job-name=s2-bulk
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --exclude=node302
#SBATCH --output=/n/fs/resemble/homogenizing-science/code/fulltext-push/logs/s2-bulk-%A_%a.out
# 2026-11-04 Semantic Scholar bulk datasets, streamed on Slurm and filtered to our lab papers (fulltext-push/s2_bulk.py).
# DATASET=papers|s2orc, array 0..15 (16 tasks, one shard stream each; nothing but the filtered rows is written). Submit with
#   sbatch --array=0-15 --export=ALL,DATASET=papers,... (from the code root, SNAPSHOT_REPO / CS_ATLAS_SNAPSHOT_COMMIT pin the code)
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
cd "$CS_ATLAS_CODE"
sleep $(( (SLURM_ARRAY_TASK_ID % 16) * 5 ))   # stagger the file-list requests (the S2 key's limit is shared)
$CS_ATLAS_PY -I -u "$CS_ATLAS_FULLTEXT_PUSH/s2_bulk.py" ${DATASET:-papers} "$SLURM_ARRAY_TASK_ID" 16
