#!/bin/bash
# One stage of an `atlas pipeline` (ROADMAP #34): runs the stage's command from a code snapshot. Submitted by tools/atlas_pipeline.py, never by hand:
# it sets PIPE_CMD (from the pipeline registry), PIPE_PY (project | collector), SCHOOL_LIST, and for a per-school stage an --array over SCHOOL_LIST.
# In PIPE_CMD, {school} is this array task's school and {schools} the whole list; PY is the interpreter, TOOLS and FTP the snapshot's code directories.
#SBATCH --job-name=cs-pipeline
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
set -u -o pipefail
: "${PIPE_CMD:?}" "${PIPE_PY:?}" "${SCHOOL_LIST:?}"
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # submit from the code root
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1  # code of one commit, data in the main checkout (docs/CONTRIBUTING.md)
cd "$CS_ATLAS_WORK"
case $PIPE_PY in project) PY="nice -n 5 $CS_ATLAS_PY -u" ;; collector) PY="nice -n 5 $CS_ATLAS_COLLECTOR_PY -I -u" ;; *) echo "PIPE_PY must be project or collector"; exit 1 ;; esac
TOOLS=$CS_ATLAS_TOOLS; FTP=$CS_ATLAS_FULLTEXT_PUSH
read -r -a _S <<< "$SCHOOL_LIST"
school=${_S[${SLURM_ARRAY_TASK_ID:-0}]:-}
cmd=${PIPE_CMD//\{school\}/$school}; cmd=${cmd//\{schools\}/$SCHOOL_LIST}
echo "== pipeline stage ${PIPE_STAGE:-?}: $cmd ($(date +%F\ %T))"
eval "$cmd"; rc=$?
echo "== rc=$rc $(date +%F\ %T)"
exit $rc
