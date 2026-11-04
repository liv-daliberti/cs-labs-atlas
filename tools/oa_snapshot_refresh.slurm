#!/bin/bash
# The OpenAlex snapshot refresh (ROADMAP #24, docs/OPENALEX-SNAPSHOT.md section 14). Two uses:
#  - the monthly check (no argument): `atlas submit tools/oa_snapshot_refresh.slurm`. It first resubmits itself for the same day next month
#    (--begin, the loop_job.sh pattern: no crontab), then submits the filter -> merge -> compare chain when the bucket has a newer date than
#    `current`. `current` never moves here unless the job was submitted with OA_REFRESH_PROMOTE=1.
#  - a chain step (the argument `compare` or `promote`, with OA_REFRESH_DATE), submitted by oa_snapshot_refresh.py.
# Light: one manifest request and a few sbatch calls (compare reads two SQLite stores).
#SBATCH --job-name=oa-snapshot-refresh
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=fulltext-push/logs/oa-snapshot-refresh-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
step=${1:-auto}
if [ "$step" = auto ]; then
  . "$CS_ATLAS_FULLTEXT_PUSH/loop_job.sh"
  RESTART_LOG=/dev/stdout _resubmit --begin="$(date -d '+1 month' +%Y-%m-%dT%H:%M:%S)" "$CS_ATLAS_CODE/tools/oa_snapshot_refresh.slurm"
fi
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/oa_snapshot_refresh.py" "$step"
