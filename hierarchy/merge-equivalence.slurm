#!/bin/bash
# The merge step of a parallel equivalence run (ROADMAP #32): after every array task of hierarchy/build-school.slurm (MODE=equiv) succeeded,
# compare $RUN/old with $RUN/new, validate the new packages and list the accepted lab-page papers wired or set aside. Same reports as
# hierarchy/build-equivalence.slurm. Submitted by hierarchy/submit-parallel.sh with --dependency=afterok:<array job>.
#SBATCH --job-name=cs-merge-equiv
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:40:00
set -u -o pipefail
: "${RUN:?RUN=<shared scratch directory of the array>}" "${REPORT:?REPORT=<directory for the diff report>}" "${SCHOOL_LIST:?SCHOOL_LIST}" "${ARRAY_JOB:?ARRAY_JOB}"
NEW_CODE=${NEW_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$NEW_CODE/paths.sh" || exit 1
T=/tmp/$USER-$SLURM_JOB_ID
mkdir -p "$T" "$REPORT" || exit 1
trap 'rm -rf "$T"' EXIT
SNAPSHOT_REPO="$NEW_CODE" CS_ATLAS_SNAPSHOT_COMMIT=${CS_ATLAS_SNAPSHOT_COMMIT:-$(git -C "$NEW_CODE" rev-parse HEAD)} SNAPSHOT_DIR="$T/code" . "$NEW_CODE/tools/job_code_snapshot.sh" || exit 1
fail=0
echo "== old vs new, merged from $ARRAY_JOB: $SCHOOL_LIST $(date +%F\ %T)"
"$CS_ATLAS_PY" "$CS_ATLAS_TOOLS/package_diff.py" "$RUN/old" "$RUN/new" --schools $SCHOOL_LIST --ignore report.json:builtAt report.json:provenance.at report.json:provenance.code \
  --json "$REPORT/equivalence-$ARRAY_JOB.json" | tee "$REPORT/equivalence-$ARRAY_JOB.txt" || fail=1
"$CS_ATLAS_PY" "$CS_ATLAS_TOOLS/wired_additions_report.py" "$RUN/new" --schools $SCHOOL_LIST --json "$REPORT/wired-additions-$ARRAY_JOB.json" | tee "$REPORT/wired-additions-$ARRAY_JOB.txt"
mkdir -p "$T/vroot" && ln -sfn "$RUN/new" "$T/vroot/hierarchy"
"$CS_ATLAS_PY" "$CS_ATLAS_TOOLS/validate.py" $SCHOOL_LIST --root "$T/vroot" --json "$REPORT/validate-$ARRAY_JOB.json" | tee "$REPORT/validate-$ARRAY_JOB.txt" || fail=1
[ "${KEEP_RUN:-0}" = 1 ] || rm -rf "$RUN"
echo "== done $(date +%F\ %T) fail=$fail"
exit $fail
