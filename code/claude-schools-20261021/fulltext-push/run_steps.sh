#!/bin/sh
# Run lab_channels.py steps for one school, one at a time (each its own process, so one failing step does not stop the
# rest). One arXiv-bulk user at a time: this script is the only channel runner; it waits for an earlier one to finish.
# usage: run_steps.sh <school> <step> [<step> ...]   log -> logs/steps-<school>.log
cd "$(dirname "$0")"
PY="/usr/local/anaconda3/2024.02/bin/python -I -u"
school=$1; shift
exec 9>>logs/run_steps.lock
flock 9
for step in "$@"; do
  echo "{\"at\": \"$(date -u +%FT%TZ)\", \"start\": \"$school $step\"}"
  nice -n 5 $PY lab_channels.py $school $step || echo "{\"failed\": \"$school $step\"}"
done
echo "{\"at\": \"$(date -u +%FT%TZ)\", \"done\": \"$school $*\"}"
