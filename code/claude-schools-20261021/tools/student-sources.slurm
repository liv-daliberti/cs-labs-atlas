#!/bin/bash
#SBATCH --job-name=student-sources
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --exclude=node302,node014,node805,node808
#SBATCH --output=hierarchy/logs/student-sources-%j.log
set -euo pipefail
. "${CS_ATLAS_CODE:-$SLURM_SUBMIT_DIR}/paths.sh"
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh"
"$CS_ATLAS_PY" -I "$CS_ATLAS_TOOLS/labpage_students_school.py" sources "${SCHOOL:?SCHOOL}" \
    --seeds "${SEEDS:?SEEDS}" --out "${SOURCE_OUT:?SOURCE_OUT}" \
    --hierarchy "${SOURCE_HIERARCHY:-$CS_ATLAS_HIERARCHY}" --max-fetches "${MAX_FETCHES:-100}"
