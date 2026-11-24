#!/bin/bash
# Proof for the data-layout move (ROADMAP item 10): the packages built before the move (flat layout) and after it (split layout) are identical.
# Both builds write to scratch (PI_HIERARCHY_OUT), never to the live packages; both run the code of one commit (tools/job_code_snapshot.sh).
#   before the move:  MODE=ref REF=<dir> atlas submit hierarchy/layout-equivalence.slurm     builds every school with the code of HEAD (flat data)
#   after the move:   MODE=cmp REF=<dir> REPORT=<dir> atlas submit hierarchy/layout-equivalence.slurm
#                                                                                           builds with HEAD (split data) and diffs against REF
# package_diff ignores the build timestamps, provenance.code and provenance.inputs paths (their hashes are compared: report.json provenance.*.sha256
# must be equal; the paths differ by design) - see the final lines. SCHOOLS defaults to every released school. Check with sbatch --test-only first.
#SBATCH --job-name=cs-layout-equiv
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=3
#SBATCH --mem=40G
#SBATCH --time=03:00:00
set -u -o pipefail
: "${MODE:?MODE=ref|cmp}" "${REF:?REF=<directory for the reference packages>}"
NEW_CODE=${NEW_CODE:-${SLURM_SUBMIT_DIR:?}}
. "$NEW_CODE/paths.sh" || exit 1
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
export PYTHONHASHSEED=${PYTHONHASHSEED:-0}
T=/tmp/$USER-$SLURM_JOB_ID
mkdir -p "$T" "$REF" || exit 1
trap 'rm -rf "$T"' EXIT
SNAPSHOT_REPO="$NEW_CODE" CS_ATLAS_SNAPSHOT_COMMIT=$(git -C "$NEW_CODE" rev-parse HEAD) SNAPSHOT_DIR="$T/code" . "$NEW_CODE/tools/job_code_snapshot.sh" || exit 1
unset CS_ATLAS_SNAPSHOT_COMMIT
OUT=$T/out; [ "$MODE" = ref ] && OUT=$REF
mkdir -p "$OUT"
echo "== layout equivalence MODE=$MODE commit $(git -C "$NEW_CODE" rev-parse --short HEAD) data layout ${CS_ATLAS_DATA_LAYOUT:-default} schools: $SCHOOLS $(date +%F\ %T)"
fail=0
for s in $SCHOOLS; do
  PI_HIERARCHY_OUT="$OUT" nice -n10 "$CS_ATLAS_PY" -u "$CS_ATLAS_TOOLS/pi_hierarchy.py" "$s" > "$T/build-$s.log" 2>&1 || { echo "FAILED build $s"; tail -5 "$T/build-$s.log"; fail=1; }
  echo "   $s built $(date +%T): $(tail -1 "$T/build-$s.log" | cut -c1-200)"
done
if [ "$MODE" = cmp ]; then
  : "${REPORT:?REPORT=<directory for the diff report>}"; mkdir -p "$REPORT"
  "$CS_ATLAS_PY" "$CS_ATLAS_TOOLS/package_diff.py" "$REF" "$OUT" --schools $SCHOOLS \
     --ignore report.json:builtAt report.json:provenance \
     --json "$REPORT/layout-equivalence-$SLURM_JOB_ID.json" | tee "$REPORT/layout-equivalence-$SLURM_JOB_ID.txt" || fail=1
  # the provenance paths differ by design (raw/, reviewed/ ...); the INPUT HASHES must be equal: compare the sorted sha256 leaves
  "$CS_ATLAS_PY" - "$REF" "$OUT" $SCHOOLS <<'PY' | tee -a "$REPORT/layout-equivalence-$SLURM_JOB_ID.txt" || fail=1
import json, re, sys
ref, out, *schools = sys.argv[1:]
def leaves(o, acc):
    if isinstance(o, dict):
        for v in o.values(): leaves(v, acc)
    elif isinstance(o, list):
        for v in o: leaves(v, acc)
    elif isinstance(o, str) and re.fullmatch(r"[0-9a-f]{64}", o): acc.append(o)
    return acc
bad = 0
for s in schools:
    a, b = (sorted(leaves(json.load(open(f"{d}/{s}/report.json")).get("provenance"), [])) for d in (ref, out))
    print(f"provenance input hashes {s}: {'identical' if a == b else 'DIFFER'} ({len(a)} vs {len(b)})")
    bad += a != b
sys.exit(1 if bad else 0)
PY
fi
echo "== done $(date +%F\ %T) fail=$fail"
exit $fail
