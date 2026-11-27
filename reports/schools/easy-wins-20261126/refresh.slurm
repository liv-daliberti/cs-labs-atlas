#!/bin/bash
#SBATCH --job-name=easywins-table40
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:40:00
#SBATCH --output=/n/fs/resemble/homogenizing-science/scratch/easy-wins-1to10-1126/final-table/refresh-%j.log
set -euo pipefail
. /n/fs/resemble/homogenizing-science/code/paths.sh
export TMPDIR=/dev/shm/easywins-table-${SLURM_JOB_ID}
mkdir -p "$TMPDIR"
trap 'rm -rf "$TMPDIR"' EXIT
export CS_ATLAS_SNAPSHOT_COMMIT=075b0cd2
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh"
"$CS_ATLAS_PY" -u /n/fs/resemble/homogenizing-science/scratch/easy-wins-1to10-1126/final-table/refresh.py
