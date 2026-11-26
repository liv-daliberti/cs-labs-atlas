#!/bin/bash
# fieldft.py fetch: one chunk of open-venue PDFs (ACL Anthology / PMLR / NeurIPS / OpenReview) -> text sections; PDFs never kept. 1 core, polite 1 req/s.
#SBATCH --job-name=e32-fieldft
#SBATCH --partition=all
#SBATCH --account=allcs
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --time=00:59:00
#SBATCH --exclude=node302,node014
#SBATCH --output=/n/fs/resemble/homogenizing-science/studies/homogenization/work/entropy32-20261123/logs/fieldft-%A_%a.out
set -uo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONDONTWRITEBYTECODE=1
cd /n/fs/resemble/homogenizing-science/worktrees/ai-entropy-32/ai-writing/entropy32
$CS_ATLAS_ENV_PY -u fieldft.py fetch "$SLURM_ARRAY_TASK_ID" --budget 3100
