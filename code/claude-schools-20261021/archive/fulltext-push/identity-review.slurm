#!/bin/bash
#SBATCH --job-name=identity-review
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=06:00:00
#SBATCH --output=fulltext-push/logs/identity-review-%j.out
# 2026-10-31: the automatic identity review of the copies accepted as provider_link_only_review_pending
# (fulltext-push/identity_review.py). STEP=plan (default) writes the verdicts for review; STEP=apply applies them.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1  # submit from the code root
cd "$CS_ATLAS_WORK"
which pdftotext pdfinfo || exit 1
nice -n 5 $CS_ATLAS_PY -u fulltext-push/identity_review.py ${STEP:-plan} ${SCHOOLS:-princeton cmu epfl mit berkeley stanford} ${SCOPE:-}
