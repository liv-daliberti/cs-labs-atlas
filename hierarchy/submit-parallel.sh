#!/bin/bash
# Submit a per-school PARALLEL run (ROADMAP #32): one Slurm array task per school plus a merge job, chained with dependencies.
#   hierarchy/submit-parallel.sh equivalence OLD=<commit> REPORT=<dir> [SCHOOLS="a b"] [KEEP_RUN=1] [--test-only]
#       builds old and new for every school side by side (targets about 15 min: the slowest school), then diffs, validates, lists wired papers
#   hierarchy/submit-parallel.sh rebuild [SCHOOLS="a b"] [ALLOW_SWINGS=1] [--test-only]
#       snapshot stage -> one build task per school -> the rest of the rebuild (ids, copies, ledger, reader, audits, evidence, tests,
#       regression, validate, release, tree, housekeeping) with the same TAG (target about 45 min instead of the serial rebuild's ~2 h)
# The code is main's HEAD now (CS_ATLAS_SNAPSHOT_COMMIT is pinned for every job); run it from the code root or a worktree. Jobs on mltheory, not on node302.
set -eu
cd "$(dirname "${BASH_SOURCE[0]}")/.."
. ./paths.sh
kind=${1:?equivalence|rebuild}; shift
test_only=; extra=()
for a in "$@"; do case $a in --test-only) test_only=--test-only ;; *=*) export "$a" ;; *) echo "unknown argument $a"; exit 2 ;; esac; done
SCHOOLS=${SCHOOLS:-$CS_ATLAS_SCHOOLS}
n=$(wc -w <<< "$SCHOOLS")
export SCHOOL_LIST="$SCHOOLS" CS_ATLAS_SNAPSHOT_COMMIT=${CS_ATLAS_SNAPSHOT_COMMIT:-$(git rev-parse HEAD)} NEW_CODE=$PWD
sub() { sbatch --parsable $test_only --export=ALL "$@"; }
case $kind in
  equivalence)
    : "${OLD:?OLD=<commit of the old builder>}" "${REPORT:?REPORT=<directory for the diff report>}"
    export MODE=equiv RUN=${RUN:-$CS_ATLAS_SCRATCH/equiv-$$-$(date +%s)} OLD REPORT
    a=$(sub --array=0-$((n-1)) --output="$PWD/hierarchy/logs/build-school-%A_%a.out" hierarchy/build-school.slurm)
    [ -z "$test_only" ] || { echo "test-only: the array job passes ($a); the merge job depends on it and is checked when it is submitted"; exit 0; }
    export ARRAY_JOB=$a
    m=$(sub --dependency=afterok:$a --output="$PWD/hierarchy/logs/merge-equivalence-%j.out" hierarchy/merge-equivalence.slurm)
    echo "equivalence: array $a ($n schools: $SCHOOLS), merge $m; run dir $RUN; report $REPORT" ;;
  rebuild)
    export TAG=${TAG:-rebuild-par-$(date +%Y%m%d-%H%M%S)} MODE=build
    j1=$(STAGES=snapshot sub --output="$PWD/hierarchy/logs/rebuild-snapshot-%j.out" hierarchy/rebuild-all.slurm)
    [ -z "$test_only" ] || { echo "test-only: the snapshot job passes ($j1); the array and the rest depend on it and are checked when submitted"; exit 0; }
    j2=$(sub --dependency=afterok:$j1 --array=0-$((n-1)) --output="$PWD/hierarchy/logs/build-school-%A_%a.out" hierarchy/build-school.slurm)
    j3=$(STAGES="ids copies ledger reader audits evidence tests regression validate release tree housekeeping" sub --dependency=afterok:$j2 \
         --output="$PWD/hierarchy/logs/rebuild-rest-%j.out" hierarchy/rebuild-all.slurm)
    echo "rebuild $TAG: snapshot $j1 -> build array $j2 ($n schools: $SCHOOLS) -> rest $j3" ;;
  *) echo "equivalence|rebuild"; exit 2 ;;
esac
