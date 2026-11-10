#!/bin/bash
# Channels for one school as a restartable snapshot job: SCHOOL=<school> CHANNELS="labpages pihomes" atlas submit fulltext-push/school-channels.slurm
# (run_steps.sh's per-channel locks apply; logs go to the shared FT_LOGS). 2026-11-01: Michigan's labpages and pihomes.
# 2026-11-10: 59 minutes on partition all (a 6 h mltheory job waited days in the queue) and self-restarting like the loops (USR1 900 s before the limit, loop_job.sh;
# the steps resume from the catalog and the channel caches); it ends when run_steps.sh finishes its list. OA_RESERVE=4000, WAYBACK_HOLD=1 (docs/CHANNELS.md).
#SBATCH --job-name=school-channels
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:59:00
#SBATCH --signal=B:USR1@900
#SBATCH --output=fulltext-push/logs/school-channels-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # submit from the code root
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
: "${SCHOOL:?set SCHOOL}" "${CHANNELS:?set CHANNELS}"
. "$CS_ATLAS_CODE/fulltext-push/loop_job.sh"
refuse_if_downloads_stopped
export OA_RESERVE="${OA_RESERVE:-4000}" WAYBACK_HOLD="${WAYBACK_HOLD:-1}" WAYBACK_LOW=1   # OpenAlex floor 4,000; Wayback left to the listing captures
RESTART_LOG="$CS_ATLAS_FT_LOGS/steps-$SCHOOL.restarts"
run_restartable "fulltext-push/school-channels.slurm" -- ./run_steps.sh "$SCHOOL" $CHANNELS >> "$CS_ATLAS_FT_LOGS/steps-$SCHOOL.log" 2>&1 < /dev/null
