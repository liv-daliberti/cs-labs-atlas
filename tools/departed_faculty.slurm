#!/bin/bash
# The departed-faculty review list (ROADMAP #26): atlas submit tools/departed_faculty.slurm  -> hierarchy/derived/departed-faculty-review.json
#SBATCH --job-name=departed-faculty
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=03:00:00
#SBATCH --output=fulltext-push/logs/departed-faculty-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/departed_faculty.py" ${DEPARTED_ARGS:-}
