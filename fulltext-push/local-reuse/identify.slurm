#!/bin/bash
# Local-reuse inventory pass 2: identify.py, 16 shards, at most 6 at once (shared-storage reads: each file read once).
#SBATCH --job-name=localreuse-ident
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=04:00:00
#SBATCH --array=0-15%6
#SBATCH --output=fulltext-push/local-reuse/logs/ident-%A_%a.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
cd ${CS_ATLAS_FULLTEXT_PUSH}/local-reuse
nice -n 10 ionice -c3 ${CS_ATLAS_PY} -I identify.py $SLURM_ARRAY_TASK_ID 16
