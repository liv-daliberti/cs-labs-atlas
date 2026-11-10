#!/bin/bash
# Full-text collection for ONE protocol school (stage 8), the generalisation of michigan-collector.slurm: SCHOOL=<key> [CHANNELS="..."] atlas submit
# [--from-worktree] fulltext-push/school-collector.slurm. The open-copy channel steps (run_steps.sh, per-channel locks shared with the other schools)
# and the lab-first download loop run side by side and resume from what the school's catalog already records (add_works.py <key> seeds it first, on
# the login host). Compute nodes have no /usr/local/anaconda3, so the channels, the loop and the collector child run on the project env (shared
# storage. Restart-proof since 2026-11-05 (Georgia Tech): USR1 arrives 900 s before the limit, the loop is stopped cleanly and this script is resubmitted
# by loop_job.sh (`atlas submit` of the script itself, with SCHOOL and CHANNELS from the environment); scancel stops it for good.
#SBATCH --job-name=school-fulltext
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=3-00:00:00
#SBATCH --signal=B:USR1@900   # near the limit: stop the loop cleanly and resubmit this script (loop_job.sh, ROADMAP #18)
#SBATCH --output=fulltext-push/logs/school-collector-%j.out
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh" || exit 1
: "${SCHOOL:?set SCHOOL}"
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"
export FTP_PY="$CS_ATLAS_COLLECTOR_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
refuse_if_downloads_stopped   # disk guard marker (2026-11-10)
export WAYBACK_HOLD="${WAYBACK_HOLD:-1}"   # loops leave web.archive.org to the listing captures (collector_quality.wayback_held); WAYBACK_HOLD=0 to allow
# 2026-11-10 (owner): schools not yet admitted (no hierarchy/<school>/derived/lab_papers.jsonl.gz) take their lab papers from a copy of the registered package kept in
# scratch/downloads-1110/hierarchy-onboard/<school>/ (MANIFEST.txt has the source paths and sha256). The path is chosen at every (re)start, so the loop follows the live
# hierarchy as soon as the school is admitted.
ONBOARD="$CS_ATLAS_ROOT/scratch/downloads-1110/hierarchy-onboard"
LIVE_H="$CS_ATLAS_CODE/hierarchy"   # not $CS_ATLAS_HIERARCHY: a loop resubmits itself with its environment, so an earlier override must not stick after admission
if [ -e "$LIVE_H/$SCHOOL/derived/lab_papers.jsonl.gz" ]; then export CS_ATLAS_HIERARCHY="$LIVE_H"
elif [ -e "$ONBOARD/$SCHOOL/derived/lab_papers.jsonl.gz" ]; then export CS_ATLAS_HIERARCHY="$ONBOARD"; fi
RESTART_LOG="$CS_ATLAS_FT_LOGS/lab_first_loop-$SCHOOL.out"
# channels: the charter's [collector].channels, else the default list below. The CHANNELS environment is IGNORED unless CHANNELS_FORCE=1: a loop resubmits
# itself with its environment, so a CHANNELS set at the first submission pinned the list for ever and hid the charter (2026-11-10).
if [ "${CHANNELS_FORCE:-0}" != 1 ] || [ -z "${CHANNELS:-}" ]; then
    CHANNELS=$(PYTHONPATH="$CS_ATLAS_CODE/tools" "$CS_ATLAS_PY" -c "import school_config as S; print(' '.join(S.field(S.get('$SCHOOL'), 'collector.channels', []) or []))" 2>/dev/null)
fi
export OA_RESERVE="${OA_RESERVE:-4000}"   # OpenAlex: stop at 4,000 credits left of the shared 10,000 a day (oa_refresh.RESERVE)
./run_steps.sh "$SCHOOL" ${CHANNELS:-oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages pihomes} \
    >> "$CS_ATLAS_FT_LOGS/steps-$SCHOOL.log" 2>&1 < /dev/null &
EXTRA_PIDS=($!)
run_restartable "fulltext-push/school-collector.slurm" -- \
    nice -n 5 $CS_ATLAS_COLLECTOR_PY -I -u lab_first_loop.py "$SCHOOL" --recent-first 2023 \
    >> "$CS_ATLAS_FT_LOGS/lab_first_loop-$SCHOOL.out" 2>&1 < /dev/null
rc=$?
wait
exit $rc
