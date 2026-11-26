#!/bin/bash
# One link of a resumable `cs_related_school.py units <key>` chain (Wayback is slow on the shared clock: a link does what it can in its time limit; stored CDX answers and
# captures are reused, so the next link, submitted with --dependency=afterany:<previous>, continues). A link exits at once when units-done.json already covers every unit.
#   UNITS_KEY=kaist atlas submit [--from-worktree] [--dependency=afterany:<jobid>] tools/units_chain.slurm
#SBATCH --job-name=units-chain
#SBATCH --partition=all
#SBATCH --account=mltheory
#SBATCH --exclude=node302,node014
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=06:00:00
#SBATCH --output=fulltext-push/logs/units-chain-%j.out
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
: "${UNITS_KEY:?set UNITS_KEY}"
if "$CS_ATLAS_PY" "$CS_ATLAS_TOOLS/cs_related_school.py" units-check "$UNITS_KEY"; then echo "units-done covers every unit of $UNITS_KEY"; exit 0; fi
exec nice -n 5 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/cs_related_school.py" units "$UNITS_KEY"
