#!/bin/bash
# A scratch rebuild of one school's package (no release, nothing live is written): the lab-paper gain of an OpenAlex refresh is the
# difference between the 'before' and 'after' roots (tools/package_diff.py, or count lab_papers.jsonl.gz).
#   atlas submit --array=0-8 --export=ALL,OUT=<scratch dir>,SCHOOL_LIST="princeton cmu ..." tools/oa_refresh_build.slurm
# The builder reads the live inputs and writes <OUT>/<school>/ (PI_HIERARCHY_OUT); PYTHONHASHSEED is fixed so two runs are comparable.
#SBATCH --job-name=oa-refresh-build
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=3
#SBATCH --mem=40G
#SBATCH --time=02:00:00
#SBATCH --output=hierarchy/logs/oa-refresh-build-%A_%a.out
set -u -o pipefail
: "${OUT:?OUT=<scratch dir>}" "${SCHOOL_LIST:?SCHOOL_LIST}"
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
export PYTHONHASHSEED=0
read -r -a _S <<< "$SCHOOL_LIST"
school=${_S[$SLURM_ARRAY_TASK_ID]:?no school for this array index}
mkdir -p "$OUT" || exit 1
echo "== scratch build $school -> $OUT $(date +%F\ %T)"
PI_HIERARCHY_OUT="$OUT" nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$school"
