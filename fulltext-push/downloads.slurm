#!/bin/bash
# 2026-10-29: the lab-first download loop for each school, one array task per school (the per-school collector scripts
# also re-ran every open-copy channel; those finished on 10-29, so a restart only needs the loops).
#SBATCH --job-name=fulltext-downloads
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-5
#SBATCH --output=/n/fs/resemble/cs-atlas/work/fulltext-push/logs/downloads-%A_%a.out
SCHOOLS=(princeton cmu epfl mit berkeley stanford)
s=${SCHOOLS[$SLURM_ARRAY_TASK_ID]}
. /n/fs/resemble/cs-atlas/work/paths.sh  # every path in one place (tools/atlas_paths.py)
cd "$CS_ATLAS_FULLTEXT_PUSH"
exec nice -n 5 /usr/local/anaconda3/2024.02/bin/python -I -u lab_first_loop.py $s --recent-first 2023 >> logs/lab_first_loop-$s.out 2>&1 < /dev/null
