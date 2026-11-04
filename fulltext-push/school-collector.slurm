#!/bin/bash
# Full-text collection for ONE protocol school (stage 8), the generalisation of michigan-collector.slurm: SCHOOL=<key> [CHANNELS="..."] atlas submit
# [--from-worktree] fulltext-push/school-collector.slurm. The open-copy channel steps (run_steps.sh, per-channel locks shared with the other schools)
# and the lab-first download loop run side by side and resume from what the school's catalog already records (add_works.py <key> seeds it first, on
# the login host). Compute nodes have no /usr/local/anaconda3, so the channels, the loop and the collector child run on the project env (shared
# storage). The loop is not self-restarting (downloads.slurm has a hand-kept array slot per school): resubmit this script when it ends at the limit.
#SBATCH --job-name=school-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --output=fulltext-push/logs/school-collector-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
: "${SCHOOL:?set SCHOOL}"
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"
export FTP_PY="$CS_ATLAS_COLLECTOR_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
./run_steps.sh "$SCHOOL" ${CHANNELS:-oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages pihomes wayback_acm} \
    >> "$CS_ATLAS_FT_LOGS/steps-$SCHOOL.log" 2>&1 < /dev/null &
CH=$!
trap 'kill $CH 2>/dev/null' TERM INT
nice -n 5 $CS_ATLAS_COLLECTOR_PY -I -u lab_first_loop.py "$SCHOOL" --recent-first 2023 >> "$CS_ATLAS_FT_LOGS/lab_first_loop-$SCHOOL.out" 2>&1 < /dev/null
rc=$?
wait
exit $rc
