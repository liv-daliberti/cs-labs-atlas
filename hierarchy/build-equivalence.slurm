#!/bin/bash
# Old builder vs new builder on the same inputs, for refactors that must not change any output (ROADMAP items 5 and 8).
# For each school the old code (tools/ of commit $OLD, exported to node-local /tmp) and the new code (tools/ of the
# checkout this is submitted from) run tools/pi_hierarchy.py side by side, at the same moment, on the same live inputs,
# each with PI_HIERARCHY_OUT in node-local /tmp: no live package is written. tools/package_diff.py then compares every
# package file canonically, ignoring only the two build timestamps. Both builds hash their inputs into
# report.json -> provenance (inputs, reviewed_inputs, sweep, pi-works, DBLP), so equal provenance shows equal inputs.
#   OLD=<commit> REPORT=<dir> [SCHOOLS="a b"] [CONTROL="cmu"] sbatch hierarchy/build-equivalence.slurm   (from the new checkout's root)
# Both builders run with the same PYTHONHASHSEED (default 0): the builder's output depends on str hash order in places
# (2026-10-31: re-captured relation evidence shared by several labs, R-STU-08), so two runs of the same code with
# different seeds can differ. CONTROL=<schools> also builds those schools with the OLD code under PYTHONHASHSEED=1 and
# compares it with the seed-0 old build, to show that seed dependence apart from the refactor. CONTROL_CODE=new builds
# the control with the NEW code instead (compared with the seed-0 new build): a determinism check of the new code.
# Check with `sbatch --test-only` first.
#SBATCH --job-name=cs-hier-equiv
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=3
#SBATCH --mem=40G
#SBATCH --time=03:00:00
set -u -o pipefail
: "${OLD:?OLD=<commit of the old builder>}" "${REPORT:?REPORT=<directory for the diff report>}"
NEW_CODE=${NEW_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$NEW_CODE/paths.sh" || exit 1   # data slots: the main checkout (tools/atlas_paths.py)
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
export PYTHONHASHSEED=${PYTHONHASHSEED:-0}
CONTROL=${CONTROL:-}
CONTROL_CODE=${CONTROL_CODE:-old}
VALIDATE=${VALIDATE:-}   # 1: also validate the new packages against schemas/ (tools/validate.py)
case $CONTROL_CODE in old|new) ;; *) echo "CONTROL_CODE must be old or new"; exit 1 ;; esac
T=/tmp/$USER-$SLURM_JOB_ID
mkdir -p "$T/old-code" "$T/old" "$T/new" "$T/control" "$REPORT" || exit 1
trap 'rm -rf "$T"' EXIT
git -C "$NEW_CODE" archive "$OLD" tools | tar -x -C "$T/old-code" || exit 1
cd "$T" || exit 1
echo "== equivalence old=$OLD new=$NEW_CODE ($(git -C "$NEW_CODE" rev-parse --short HEAD)) schools: $SCHOOLS PYTHONHASHSEED=$PYTHONHASHSEED control: ${CONTROL:-none} $(date +%F\ %T)"
fail=0
if [ "$CONTROL_CODE" = new ]; then CTL_TOOL="$NEW_CODE/tools/pi_hierarchy.py"; CTL_BASE="$T/new"; else CTL_TOOL="$T/old-code/tools/pi_hierarchy.py"; CTL_BASE="$T/old"; fi
for s in $SCHOOLS; do
  echo "== $s $(date +%F\ %T)"
  PI_HIERARCHY_OUT="$T/old" nice -n10 "$CS_ATLAS_PY" -u "$T/old-code/tools/pi_hierarchy.py" "$s" > "$T/old-$s.log" 2>&1 &
  po=$!
  PI_HIERARCHY_OUT="$T/new" nice -n10 "$CS_ATLAS_PY" -u "$NEW_CODE/tools/pi_hierarchy.py" "$s" > "$T/new-$s.log" 2>&1 &
  pn=$!
  pc=
  case " $CONTROL " in *" $s "*)   # the control runs at the same moment, on the same inputs
    PYTHONHASHSEED=1 PI_HIERARCHY_OUT="$T/control" nice -n10 "$CS_ATLAS_PY" -u "$CTL_TOOL" "$s" > "$T/control-$s.log" 2>&1 &
    pc=$! ;;
  esac
  wait $po; ro=$?; wait $pn; rn=$?; rc=0; [ -n "$pc" ] && { wait $pc; rc=$?; }
  echo "   exit old=$ro new=$rn${pc:+ control($CONTROL_CODE, seed 1)=$rc} $(date +%F\ %T)"
  [ $ro = 0 ] && [ $rn = 0 ] && [ $rc = 0 ] || { fail=1; tail -5 "$T/old-$s.log" "$T/new-$s.log"; }
  cmp -s <(tail -1 "$T/old-$s.log") <(tail -1 "$T/new-$s.log") && echo "   printed counts identical" || echo "   printed counts DIFFER"
done
if [ -n "$CONTROL" ]; then
  echo "== control: $CONTROL_CODE seed $PYTHONHASHSEED vs $CONTROL_CODE seed 1"
  # old code: differences are its own seed dependence (not a failure); new code: any difference is a failure
  "$CS_ATLAS_PY" "$NEW_CODE/tools/package_diff.py" "$CTL_BASE" "$T/control" --schools $CONTROL --json "$REPORT/control-$SLURM_JOB_ID.json" \
    | tee "$REPORT/control-$SLURM_JOB_ID.txt" || { [ "$CONTROL_CODE" = new ] && fail=1; }
fi
echo "== old vs new"
"$CS_ATLAS_PY" "$NEW_CODE/tools/package_diff.py" "$T/old" "$T/new" --schools $SCHOOLS --json "$REPORT/equivalence-$SLURM_JOB_ID.json" \
  | tee "$REPORT/equivalence-$SLURM_JOB_ID.txt" || fail=1
if [ -n "$VALIDATE" ]; then
  mkdir -p "$T/vroot" && ln -sfn "$T/new" "$T/vroot/hierarchy"   # validate.py --root reads <root>/hierarchy/<school>/
  echo "== validate the new packages"
  "$CS_ATLAS_PY" "$NEW_CODE/tools/validate.py" $SCHOOLS --root "$T/vroot" --json "$REPORT/validate-$SLURM_JOB_ID.json" \
    | tee "$REPORT/validate-$SLURM_JOB_ID.txt" || fail=1
fi
echo "== done $(date +%F\ %T) fail=$fail"
exit $fail
