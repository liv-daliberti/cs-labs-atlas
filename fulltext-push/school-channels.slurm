#!/bin/bash
# Channels for one school as a snapshot job: SCHOOL=<school> CHANNELS="labpages pihomes" atlas submit fulltext-push/school-channels.slurm
# (run_steps.sh's per-channel locks apply; logs go to the shared FT_LOGS). 2026-11-01: Michigan's labpages and pihomes.
#SBATCH --job-name=school-channels
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --exclude=node302
#SBATCH --output=fulltext-push/logs/school-channels-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # submit from the code root
export LD_LIBRARY_PATH="$CS_ATLAS_ENV_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CS_ATLAS_COLLECTOR_PY="$CS_ATLAS_PY"
export FTP_PY="$CS_ATLAS_PY"
. "$CS_ATLAS_CODE/fulltext-push/job_snapshot.sh" || exit 1
cd "$CS_ATLAS_FULLTEXT_PUSH"
: "${SCHOOL:?set SCHOOL}" "${CHANNELS:?set CHANNELS}"
./run_steps.sh "$SCHOOL" $CHANNELS >> "$CS_ATLAS_FT_LOGS/steps-$SCHOOL.log" 2>&1 < /dev/null
