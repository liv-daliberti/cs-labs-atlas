#!/bin/bash
# One school of a parallel build or equivalence run: a Slurm ARRAY task per school (ROADMAP #32). Submitted by hierarchy/submit-parallel.sh,
# which sets the array range and the variables below with --export; a merge job runs after all tasks (afterok).
#   MODE=build   pi_hierarchy.py <school> writes the live package (what rebuild.sh's build stage does for one school)
#   MODE=equiv   the OLD builder (git archive of $OLD) and the NEW one (this checkout's HEAD, a code snapshot) build the school side by side into
#                $RUN/old and $RUN/new on shared scratch; hierarchy/merge-equivalence.slurm compares them
# SCHOOL_LIST is the space-separated list the array indexes; RUN is a shared-scratch directory; PYTHONHASHSEED is the same for both builds.
# Check with `sbatch --test-only` first (hierarchy/submit-parallel.sh does).
#SBATCH --job-name=cs-build-school
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=3
#SBATCH --mem=40G
#SBATCH --time=02:00:00
set -u -o pipefail
: "${MODE:?MODE=build|equiv}" "${SCHOOL_LIST:?SCHOOL_LIST}"
NEW_CODE=${NEW_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$NEW_CODE/paths.sh" || exit 1
export PYTHONHASHSEED=${PYTHONHASHSEED:-0}
read -r -a _S <<< "$SCHOOL_LIST"
school=${_S[$SLURM_ARRAY_TASK_ID]:?no school for this array index}
T=/tmp/$USER-$SLURM_JOB_ID
mkdir -p "$T" || exit 1
trap 'rm -rf "$T"' EXIT
SNAPSHOT_REPO="$NEW_CODE" CS_ATLAS_SNAPSHOT_COMMIT=${CS_ATLAS_SNAPSHOT_COMMIT:-$(git -C "$NEW_CODE" rev-parse HEAD)} SNAPSHOT_DIR="$T/code" . "$NEW_CODE/tools/job_code_snapshot.sh" || exit 1
echo "== $MODE $school (array task $SLURM_ARRAY_TASK_ID) $(date +%F\ %T)"
case $MODE in
  build)
    $CS_ATLAS_PY -c "import sys; sys.path.insert(0, '$CS_ATLAS_TOOLS'); import atlas_paths as P; P.data('link-diagnosis.json', '$school').unlink(missing_ok=True)"
    nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$school"; rc=$? ;;
  equiv)
    : "${OLD:?OLD=<commit of the old builder>}" "${RUN:?RUN=<shared scratch directory>}"
    mkdir -p "$RUN/old" "$RUN/new" "$T/old-code" || exit 1
    git -C "$NEW_CODE" archive "$OLD" tools | tar -x -C "$T/old-code" || exit 1
    unset CS_ATLAS_SNAPSHOT_COMMIT   # the old build records the live checkout's commit, as before
    PI_HIERARCHY_OUT="$RUN/old" nice -n10 "$CS_ATLAS_PY" -u "$T/old-code/tools/pi_hierarchy.py" "$school" > "$RUN/old-$school.log" 2>&1 & po=$!
    PI_HIERARCHY_OUT="$RUN/new" nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$school" > "$RUN/new-$school.log" 2>&1 & pn=$!
    wait $po; ro=$?; wait $pn; rn=$?
    echo "   exit old=$ro new=$rn $(date +%T)"
    cmp -s <(tail -1 "$RUN/old-$school.log") <(tail -1 "$RUN/new-$school.log") && echo "   printed counts identical" || echo "   printed counts DIFFER"
    rc=$(( ro || rn )) ;;
  *) echo "MODE must be build or equiv"; exit 1 ;;
esac
echo "== $school done rc=$rc $(date +%F\ %T)"
exit $rc
