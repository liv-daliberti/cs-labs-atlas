#!/bin/bash
#SBATCH --job-name=oai-repo
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=48:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/oai-repo-%j.out
# 2026-11-04 institutional-repository harvests (docs/CHANNELS.md "Repository harvests"): the schools whose charter [oai_repo] says
# verdict = "harvest", one after another and one request at a time (the pace is the charter's delay or the host's Crawl-delay).
# Resumable: resubmit and it continues from the stored resumption tokens; a finished set is only re-asked for what changed.
# The match + candidate write is a separate step afterwards: run_steps.sh <school> oai_repo.
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1  # submit from the code root
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
for s in ${SCHOOLS:-uchicago epfl cmu mit}; do
  "$FTP_PY" -I -u oai_repo.py ${MODE:-harvest} $s < /dev/null
done
echo '{"oai-repo": "done"}'
