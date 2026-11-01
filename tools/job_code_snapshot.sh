# Slurm jobs run from a code snapshot (docs/CONTRIBUTING.md). Source this after paths.sh, near the top of a job script:
#     . "$CS_ATLAS_CODE/paths.sh" || exit 1
#     . "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
# It extracts the code of ONE commit into job-local scratch (git archive reads the object store, so it is exact even while a
# landing rewrites the main checkout's files) and points the code slots at it:
#     CS_ATLAS_TOOLS, TESTS, VENDOR, SCHOOL_CONFIGS, FULLTEXT_PUSH, AI_WRITING   -> $CS_ATLAS_SNAPSHOT/<dir>
# CS_ATLAS_CODE and every data slot (hierarchy/, census/, periods/, stores/, ...) keep pointing at the main checkout, so
# the job reads and writes the same data. The script then runs its tools as "$CS_ATLAS_TOOLS/x.py", not "tools/x.py".
# The commit is CS_ATLAS_SNAPSHOT_COMMIT when set (`atlas submit` sets it to main's HEAD at submit time; or sbatch
# --export=ALL,CS_ATLAS_SNAPSHOT_COMMIT=<sha>), else HEAD of the main checkout at job start. It is printed in the job log, and
# tools/provenance.py records it as report.json provenance.code.commit (with snapshot: true).
# SNAPSHOT_REPO=<checkout> takes the code from another checkout of the repository (a worktree under test; default the main
# checkout). SNAPSHOT_DIR=<dir> puts the snapshot there (the caller removes it); otherwise it is $TMPDIR/atlas-code-<user>-<jobid>,
# removed by an EXIT trap this file installs only when the caller has none (else call snapshot_remove from your trap).
_c=${CS_ATLAS_SNAPSHOT_COMMIT:-}
_how=submit
[ -n "$_c" ] || { _c=HEAD; _how=job-start; }
_c=$(git -C "${SNAPSHOT_REPO:-$CS_ATLAS_CODE}" rev-parse --verify "$_c^{commit}" 2>/dev/null) || { echo "job_code_snapshot: no such commit '${CS_ATLAS_SNAPSHOT_COMMIT:-HEAD}' in ${SNAPSHOT_REPO:-$CS_ATLAS_CODE}" >&2; return 1; }
_own=
if [ -z "${SNAPSHOT_DIR:-}" ]; then SNAPSHOT_DIR=${TMPDIR:-/tmp}/atlas-code-${USER:-u}-${SLURM_JOB_ID:-$$}; _own=1; fi
snapshot_remove() { [ -n "${CS_ATLAS_SNAPSHOT:-}" ] && rm -rf "$CS_ATLAS_SNAPSHOT"; }
mkdir -p "$SNAPSHOT_DIR" && git -C "${SNAPSHOT_REPO:-$CS_ATLAS_CODE}" archive "$_c" | tar -x -C "$SNAPSHOT_DIR" || { echo "job_code_snapshot: could not extract $_c" >&2; return 1; }
[ -z "$_own" ] || [ -n "$(trap -p EXIT)" ] || trap snapshot_remove EXIT
export CS_ATLAS_SNAPSHOT=$SNAPSHOT_DIR CS_ATLAS_SNAPSHOT_COMMIT=$_c
export CS_ATLAS_TOOLS=$SNAPSHOT_DIR/tools CS_ATLAS_TESTS=$SNAPSHOT_DIR/tests CS_ATLAS_VENDOR=$SNAPSHOT_DIR/vendor
export CS_ATLAS_SCHOOL_CONFIGS=$SNAPSHOT_DIR/schools CS_ATLAS_FULLTEXT_PUSH=$SNAPSHOT_DIR/fulltext-push CS_ATLAS_AI_WRITING=$SNAPSHOT_DIR/ai-writing
echo "code snapshot: commit $_c ($_how) at $SNAPSHOT_DIR; data stays at $CS_ATLAS_CODE"
unset _c _how _own
