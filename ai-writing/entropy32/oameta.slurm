#!/bin/bash
# oameta.py chunk: stream one chunk of the OpenAlex works snapshot; keep topic, venue and citation fields of our papers. 1 core.
#SBATCH --job-name=e32-oameta
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/oameta-%A_%a.out
set -euo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
if [ "${1:-chunk}" = merge ]; then $CS_ATLAS_ENV_PY -u oameta.py merge; else $CS_ATLAS_ENV_PY -u oameta.py chunk "$SLURM_ARRAY_TASK_ID"; fi
