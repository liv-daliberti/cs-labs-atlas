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
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse/logs/ident-%A_%a.out
cd /n/fs/resemble/cs-atlas/work/fulltext-push/local-reuse
export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib
nice -n 10 ionice -c3 /n/fs/resemble/cs-atlas-env/py310/bin/python -I identify.py $SLURM_ARRAY_TASK_ID 16
