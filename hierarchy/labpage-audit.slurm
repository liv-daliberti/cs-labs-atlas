#!/bin/bash
# Lab-page audit (tools/labpage_audit.py, docs/LAB-PAGES.md): discover -> recover -> audit for each school given.
# Network steps are paced (>= 3 s per host, Wayback 6 s) and honour robots.txt, including groups naming AI agents; a bot
# challenge is never retried (the host is then read from existing Wayback id_ captures only). One writer per school
# store: do not run another discover/recover for the same school while this runs. Check with `sbatch --test-only` first; submit with `atlas submit`.
# usage: sbatch hierarchy/labpage-audit.slurm princeton [cmu ...]      (STEPS="discover recover audit" by default;
#        ARGS="--redo-unrecorded" passes options to every step)
#SBATCH --job-name=lp-audit
#SBATCH --partition=mltheory
#SBATCH --account=mltheory
#SBATCH --exclude=node302
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=hierarchy/logs/labpage-audit-%j.out
set -u
. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  # every path in one place; submit from the code root
cd "$CS_ATLAS_WORK"
set -a; . "$HOME/.config/cs-atlas/openalex.env"; set +a   # OPENALEX_API_KEY for the recover step (never printed)
# per-job scratch for page-1 PDFs and per-host stamps (never /n/fs); node805's shared /tmp was full on 2026-10-30 (not by
# us: the job's private /tmp was empty), so check df first and fall back to /dev/shm
export TMPDIR="${SLURM_TMPDIR:-/tmp/$USER-$SLURM_JOB_ID}"
avail=$(df --output=avail -k /tmp | tail -1)
if [ "${avail:-0}" -lt 2000000 ]; then echo "/tmp has ${avail} kB free: using /dev/shm"; export TMPDIR=/dev/shm/$USER-$SLURM_JOB_ID; fi
mkdir -p "$TMPDIR" || exit 1; trap 'rm -rf "$TMPDIR"' EXIT
df -h "$TMPDIR" | tail -1
# run the code of ONE commit (docs/CONTRIBUTING.md, "Slurm jobs run from a code snapshot"); submit with `atlas submit` to pin it
# (the snapshot lives in $TMPDIR, which the trap above removes)
. "$CS_ATLAS_CODE/tools/job_code_snapshot.sh" || exit 1
PY="$CS_ATLAS_COLLECTOR_PY"; [ -x "$PY" ] || PY="$CS_ATLAS_PY"   # some nodes have no /usr/local/anaconda3
for s in "$@"; do
  for st in ${STEPS:-discover recover audit}; do
    echo "== $s $st $(date -Is)"
    nice "$PY" -I -u "$CS_ATLAS_TOOLS/labpage_audit.py" "$st" "$s" ${ARGS:-} || echo "!! $s $st failed"
  done
done
