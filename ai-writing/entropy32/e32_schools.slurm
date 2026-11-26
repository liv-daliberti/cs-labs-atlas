#!/bin/bash
# schools.py run: every analysis and figure for one school (array task = index in schools/SCHOOLS.json). CPU only.
#SBATCH --job-name=e32-schools
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/schools-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
$CS_ATLAS_ENV_PY -u schools.py run --id "${E32_ID:-20261123}"
