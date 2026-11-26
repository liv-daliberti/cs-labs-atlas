#!/bin/bash
#SBATCH --job-name=e32-field
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/field-%j.out
set -euo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=32
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
$CS_ATLAS_ENV_PY -u fieldscale.py --id "${E32_ID:-20261123}"
