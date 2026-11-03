#!/bin/bash
# identity_revert_doubtful.py plan|apply over all schools: REVERT_CMD=plan|apply atlas submit fulltext-push/identity-revert.slurm
#SBATCH --job-name=identity-revert
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=fulltext-push/logs/identity-revert-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
"$CS_ATLAS_PY" -I -u identity_revert_doubtful.py ${REVERT_CMD:-plan} ${SCHOOLS:-princeton cmu epfl mit berkeley stanford michigan}
