# A download loop that restarts itself at its Slurm time limit (ROADMAP #18, 2026-11-02).
# Source in a .slurm script that has `#SBATCH --signal=B:USR1@900`, then:  run_restartable <resubmit-script> [sbatch options...] -- <command...>
#   - the command runs as a child; USR1 (sent by Slurm 900 s before the limit) stops it cleanly with TERM, waits for it to exit
#     (the loop releases .loop.lock and stops its collector first), then resubmits the same script with `atlas submit`, which
#     pins main's HEAD at that moment, so the next run takes whatever landed since;
#   - TERM or INT (scancel, an owner stop) stops the child and does NOT resubmit: a deliberate stop stays stopped;
#   - a resubmit is refused, and logged, when `sbatch --test-only` prints "Preempts:" or fails; the loop then stays down and the
#     status page alarm shows it (collectors_status).
# EXTRA_PIDS (array) are other background processes of the job to TERM together with the child (Michigan's channel steps).
# RESTART_LOG is the file the restart lines go to (default: stdout).
_restart_log() { printf '{"at": "%s", "loop_job": %s}\n' "$(date -u +%FT%TZ)" "$1" >> "${RESTART_LOG:-/dev/stdout}"; }

_resubmit() {
  local code=${CS_ATLAS_CODE:?} out
  (
    for v in $(env | grep -o '^SLURM_[A-Z_0-9]*'); do unset "$v"; done   # a fresh submission, not a child step of this job
    unset CS_ATLAS_SNAPSHOT CS_ATLAS_SNAPSHOT_COMMIT CS_ATLAS_TOOLS CS_ATLAS_TESTS CS_ATLAS_VENDOR CS_ATLAS_SCHOOL_CONFIGS CS_ATLAS_FULLTEXT_PUSH CS_ATLAS_AI_WRITING
    cd "$code" || exit 1
    out=$("$code/bin/atlas" submit --test-only "$@" 2>&1) || { _restart_log "\"resubmit refused: test-only failed\""; exit 1; }
    case $out in *Preempts:*) _restart_log "\"resubmit refused: Preempts\""; exit 1;; esac
    out=$("$code/bin/atlas" submit "$@" 2>&1 | tail -1) || { _restart_log "\"resubmit failed\""; exit 1; }
    _restart_log "\"resubmitted: ${out//\"/}\""
  )
}

run_restartable() {
  local script=$1; shift
  local args=("$script")
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do args+=("$1"); shift; done
  shift
  RESTART=
  "$@" &
  CHILD=$!
  _stop() { kill -TERM "$CHILD" "${EXTRA_PIDS[@]}" 2>/dev/null; }
  trap '_stop' TERM INT
  trap 'RESTART=1; _stop' USR1
  local rc=0
  while kill -0 "$CHILD" 2>/dev/null; do wait "$CHILD"; rc=$?; done
  trap - TERM INT USR1
  if [ -n "$RESTART" ]; then
    _restart_log "\"time limit near: loop stopped (exit $rc), resubmitting\""
    _resubmit "${args[@]}"
  fi
  return "$rc"
}
