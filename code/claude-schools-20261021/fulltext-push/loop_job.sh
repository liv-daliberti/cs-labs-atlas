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

# 2026-11-06: the resubmission carries the standing options on the sbatch command line (a script's #SBATCH directives lose to it, and an SBATCH_* variable
# loses to the directives): partition all, account mltheory, 59 minutes (the loop restarts itself 15 min before), the bad-node excludes.
# 2026-11-10 disk guard (disk_guard.py): while $CS_ATLAS_FT_RAW/downloads_stopped_by_disk_guard exists no download job starts and none is resubmitted.
# The owner clears it by hand (rm) once space is back. The guard's own job sets LOOP_RESUBMIT_IGNORE_STOP=1 so it keeps watching.
downloads_stopped() { [ -n "${CS_ATLAS_FT_RAW:-}" ] && [ -e "$CS_ATLAS_FT_RAW/downloads_stopped_by_disk_guard" ]; }
refuse_if_downloads_stopped() {
  if downloads_stopped; then
    printf '{"at": "%s", "refused": "downloads_stopped_by_disk_guard marker exists (disk guard); remove the downloads_stopped_by_disk_guard marker in FT_RAW after freeing space"}\n' "$(date -u +%FT%TZ)"
    exit 3
  fi
}

RESUBMIT_OPTS=(--partition=all --account=mltheory --time=00:59:00 --exclude=node302,node014,node805,node808)

# 2026-11-06 bug: the options after the script name ("downloads.slurm --array=3") are the SCRIPT's arguments, not sbatch's, so every task resubmitted
# the script's whole `#SBATCH --array=0-6` (25 tasks in 6 arrays by 11:28). The sbatch options now come BEFORE the script, and a sentinel per
# (script, school, array index) refuses a second resubmission while the job it recorded is still pending or running.
_resubmit() {
  local code=${CS_ATLAS_CODE:?} out script=$1; shift
  local me="${SLURM_JOB_ID:-}" me_arr="${SLURM_ARRAY_JOB_ID:-}"   # captured before the subshell unsets SLURM_*
  local key="$(basename "$script")-${SCHOOL:-none}-${SLURM_ARRAY_TASK_ID:-none}"
  local sentinel="${CS_ATLAS_FT_LOGS:-$code/fulltext-push/logs}/.resubmitted-$key"
  (
    for v in $(env | grep -o '^SLURM_[A-Z_0-9]*'); do unset "$v"; done   # a fresh submission, not a child step of this job
    unset CS_ATLAS_SNAPSHOT CS_ATLAS_SNAPSHOT_COMMIT CS_ATLAS_TOOLS CS_ATLAS_TESTS CS_ATLAS_VENDOR CS_ATLAS_SCHOOL_CONFIGS CS_ATLAS_FULLTEXT_PUSH CS_ATLAS_AI_WRITING
    cd "$code" || exit 1
    exec 8>"$sentinel.lock"; flock 8
    prev=$(cat "$sentinel" 2>/dev/null)
    # 2026-11-06: the sentinel holds the id of the job that is resubmitting now (its predecessor wrote it), so without this test every chain
    # stopped after one generation (all 9 loops died at 18:09 UTC); only ANOTHER live job counts as "already resubmitted".
    if [ -n "$prev" ] && [ "$prev" != "$me" ] && [ "$prev" != "$me_arr" ] && [ -n "$(squeue -h -j "$prev" 2>/dev/null)" ]; then _restart_log "\"resubmit refused: $key already resubmitted as job $prev (still queued or running)\""; exit 1; fi
    out=$("$code/bin/atlas" submit --test-only "${RESUBMIT_OPTS[@]}" "$@" "$script" 2>&1) || { _restart_log "\"resubmit refused: test-only failed\""; exit 1; }
    case $out in *Preempts:*) _restart_log "\"resubmit refused: Preempts\""; exit 1;; esac
    out=$("$code/bin/atlas" submit "${RESUBMIT_OPTS[@]}" "$@" "$script" 2>&1 | tail -1) || { _restart_log "\"resubmit failed\""; exit 1; }
    case $out in *"Submitted batch job "*) echo "${out##*Submitted batch job }" | awk '{print $1}' > "$sentinel";; esac
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
  if [ -n "$RESTART" ] && [ -z "${LOOP_RESUBMIT_IGNORE_STOP:-}" ] && downloads_stopped; then
    _restart_log "\"resubmit refused: disk guard marker exists\""
  elif [ -n "$RESTART" ]; then
    _restart_log "\"time limit near: loop stopped (exit $rc), resubmitting\""
    _resubmit "${args[@]}"
  fi
  return "$rc"
}
