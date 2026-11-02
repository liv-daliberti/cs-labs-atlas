#!/bin/bash
# Identity review with every known title (snapshot, OpenAlex, S2, arXiv) and the PDF's own title metadata (ROADMAP #25).
# IDENT_CMD=plan|apply (default plan: read-only; apply takes a locked catalog backup first), SCHOOLS, IDENT_ARGS (e.g. "--alt-titles --reverted").
#SBATCH --job-name=identity-alt
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=fulltext-push/logs/identity-alt-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in ${SCHOOLS:-princeton cmu epfl mit berkeley stanford michigan}; do
  nice -n 5 "$CS_ATLAS_PY" -I -u identity_review.py ${IDENT_CMD:-plan} $s ${IDENT_ARGS:---alt-titles}
done
