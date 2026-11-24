#!/bin/bash
# The reader's polite landing-page check (tools/link_check.py): atlas submit tools/link_check.slurm  (resumes from the verdict file)
#SBATCH --job-name=link-check
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=08:00:00
#SBATCH --output=fulltext-push/logs/link-check-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/link_check.py" ${LINK_CHECK_ARGS:-}
