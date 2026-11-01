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
#SBATCH --output=fulltext-push/logs/downloads-%A_%a.out
SCHOOLS=(princeton cmu epfl mit berkeley stanford)
s=${SCHOOLS[$SLURM_ARRAY_TASK_ID]}
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place (tools/atlas_paths.py); submit from the code root
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1  # code of one commit, data shared (docs/CONTRIBUTING.md); submit with `atlas submit`
cd "$CS_ATLAS_FULLTEXT_PUSH"
# no exec: the snapshot's EXIT trap must run when the loop ends. A restart takes the then-current commit (atlas submit pins it).
nice -n 5 ${CS_ATLAS_COLLECTOR_PY} -I -u lab_first_loop.py $s --recent-first 2023 >> "$CS_ATLAS_FT_LOGS"/lab_first_loop-$s.out 2>&1 < /dev/null
