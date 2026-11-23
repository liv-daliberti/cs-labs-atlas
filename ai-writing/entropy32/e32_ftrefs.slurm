#!/bin/bash
# ftrefs.py shard: citation years from the reference sections of one e32 shard (CPU; pdftotext).
#SBATCH --job-name=e32-ftrefs
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/ftrefs-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
export TMPDIR=${TMPDIR:-/tmp}
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
$CS_ATLAS_ENV_PY -u ftrefs.py shard --id "${E32_ID:-20261123}" -j 8
