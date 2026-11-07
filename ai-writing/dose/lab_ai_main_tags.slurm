#!/bin/bash
# Provisional main-body tags for the lab AI score: sbatch --array=0-5 lab_ai_main_tags.slurm   (6 shards, ~3,300 papers each)
# Needs ai-writing/fulltext_sections.py (branch agent/fulltext-sections until it lands): taken from that branch when the snapshot has none.
#SBATCH --job-name=lab-ai-tags
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --output=ai-writing/logs/lab-ai-tags-%A_%a.out
set -euo pipefail
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
if [ ! -f "$CS_ATLAS_AI_WRITING/fulltext_sections.py" ]; then
  mkdir -p "$CS_ATLAS_SNAPSHOT/sections-src"
  git -C "$CS_ATLAS_CODE" show agent/fulltext-sections:ai-writing/fulltext_sections.py > "$CS_ATLAS_SNAPSHOT/sections-src/fulltext_sections.py"
  export AIW_SECTIONS_DIR="$CS_ATLAS_SNAPSHOT/sections-src"
fi
cd "$CS_ATLAS_AI_WRITING/dose"
$CS_ATLAS_ENV_PY -u lab_ai_main_tags.py run --shard "${SLURM_ARRAY_TASK_ID:?}" --nshards 6 --tag v1
