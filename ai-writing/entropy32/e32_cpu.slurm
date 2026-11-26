#!/bin/bash
# e32.py sections: main/appendix split of one shard's stored copies (CPU; pdftotext). Array task = shard. <= 59 min, resumable.
#SBATCH --job-name=e32-sections
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/sections-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
export TMPDIR=${TMPDIR:-/tmp}
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
$CS_ATLAS_ENV_PY -u e32.py sections --id "${E32_ID:-20261123}" --shard "$SLURM_ARRAY_TASK_ID" -j 8 --budget 3000
