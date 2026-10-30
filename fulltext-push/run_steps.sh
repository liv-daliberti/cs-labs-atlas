#!/bin/sh
# Run lab_channels.py steps for one school, one at a time (each its own process, so one failing step does not stop the
# rest). Since 2026-10-28 the lock is per channel, not global: two schools may run different channels side by side, but
# one channel (one API key, one arXiv-bulk listing, one set of hosts) never runs twice at once.
# usage: run_steps.sh <school> <step> [<step> ...]   log -> logs/steps-<school>.log
cd "$(dirname "$0")"
# FTP_PY: another interpreter (2026-10-30: compute nodes have no /usr/local/anaconda3; Slurm jobs pass the project env)
PY="${FTP_PY:-/usr/local/anaconda3/2024.02/bin/python} -I -u"
school=$1; shift
for step in "$@"; do
  (
    flock 9
    echo "{\"at\": \"$(date -u +%FT%TZ)\", \"start\": \"$school $step\"}"
    nice -n 5 $PY lab_channels.py $school $step || echo "{\"failed\": \"$school $step\"}"
  ) 9>>logs/run_steps-$step.lock
done
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"done\": \"$school $*\"}"
