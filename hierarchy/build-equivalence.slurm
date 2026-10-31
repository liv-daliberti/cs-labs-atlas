#!/bin/bash
# Old builder vs new builder on the same inputs, for refactors that must not change any output (ROADMAP items 5 and 8).
# For each school the old code (tools/ of commit $OLD, exported to node-local /tmp) and the new code (tools/ of the
# checkout this is submitted from) run tools/pi_hierarchy.py side by side, at the same moment, on the same live inputs,
# each with PI_HIERARCHY_OUT in node-local /tmp: no live package is written. tools/package_diff.py then compares every
# package file canonically, ignoring only the two build timestamps. Both builds hash their inputs into
# report.json -> provenance (inputs, reviewed_inputs, sweep, pi-works, DBLP), so equal provenance shows equal inputs.
#   OLD=<commit> REPORT=<dir> [SCHOOLS="a b"] sbatch hierarchy/build-equivalence.slurm     (from the new checkout's root)
# Check with `sbatch --test-only` first.
#SBATCH --job-name=cs-hier-equiv
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=32G
#SBATCH --time=03:00:00
set -u
: "${OLD:?OLD=<commit of the old builder>}" "${REPORT:?REPORT=<directory for the diff report>}"
NEW_CODE=${NEW_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$NEW_CODE/paths.sh" || exit 1   # data slots: the main checkout (tools/atlas_paths.py)
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
T=/tmp/$USER-$SLURM_JOB_ID
mkdir -p "$T/old-code" "$T/old" "$T/new" "$REPORT" || exit 1
trap 'rm -rf "$T"' EXIT
git -C "$NEW_CODE" archive "$OLD" tools | tar -x -C "$T/old-code" || exit 1
cd "$T" || exit 1
echo "== equivalence old=$OLD new=$NEW_CODE ($(git -C "$NEW_CODE" rev-parse --short HEAD)) schools: $SCHOOLS $(date +%F\ %T)"
fail=0
for s in $SCHOOLS; do
  echo "== $s $(date +%F\ %T)"
  PI_HIERARCHY_OUT="$T/old" nice -n10 "$CS_ATLAS_PY" -u "$T/old-code/tools/pi_hierarchy.py" "$s" > "$T/old-$s.log" 2>&1 &
  po=$!
  PI_HIERARCHY_OUT="$T/new" nice -n10 "$CS_ATLAS_PY" -u "$NEW_CODE/tools/pi_hierarchy.py" "$s" > "$T/new-$s.log" 2>&1 &
  pn=$!
  wait $po; ro=$?; wait $pn; rn=$?
  echo "   exit old=$ro new=$rn $(date +%F\ %T)"
  [ $ro = 0 ] && [ $rn = 0 ] || { fail=1; tail -5 "$T/old-$s.log" "$T/new-$s.log"; }
  cmp -s <(tail -1 "$T/old-$s.log") <(tail -1 "$T/new-$s.log") && echo "   printed counts identical" || echo "   printed counts DIFFER"
done
"$CS_ATLAS_PY" "$NEW_CODE/tools/package_diff.py" "$T/old" "$T/new" --schools $SCHOOLS --json "$REPORT/equivalence-$SLURM_JOB_ID.json" \
  | tee "$REPORT/equivalence-$SLURM_JOB_ID.txt" || fail=1
echo "== done $(date +%F\ %T) fail=$fail"
exit $fail
