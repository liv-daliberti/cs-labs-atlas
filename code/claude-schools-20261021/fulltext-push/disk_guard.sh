#!/bin/sh
# Disk guard for the full-text downloads (2026-10-26; the coordinator's rule while /n/fs/similarity is being migrated):
# every 2 minutes read the share's free space (df, never du); when it falls under 150 GB, stop the downloads - the
# school collector loops (cmu/epfl/mit_collect_loop.py, lab_first_loop.py), their collector children, and any
# Princeton pass collector - with SIGTERM (a stopped pass loses nothing: tried URLs are recorded per work), then exit.
# Candidate discovery (lab_channels / chain scripts) writes only small catalog rows and keeps running.
# log -> logs/disk-guard.log; stop it early with: touch raw/disk_guard.stop
cd "$(dirname "$0")"
. ../paths.sh  # every path in one place (tools/atlas_paths.py)
LIMIT_GB=150
while [ ! -f raw/disk_guard.stop ]; do
  free=$(df -B1G --output=avail /n/fs/similarity | tail -1 | tr -d ' ')
  if [ "$free" -lt "$LIMIT_GB" ]; then
    echo "{\"at\": \"$(date -u +%FT%TZ)\", \"free_gb\": $free, \"action\": \"stopping downloads\"}"
    for pat in 'tools/cmu_collect_loop.py' 'tools/epfl_collect_loop.py' 'tools/mit_collect_loop.py' 'lab_first_loop.py' 'princeton_pass.sh'; do
      pkill -TERM -u "$(id -u)" -f "$pat" && echo "{\"stopped\": \"$pat\"}"
    done
    sleep 5
    for pat in "collector_wrapper.py --out $CS_ATLAS_STORES" 'mit_collector_wrapper.py' 'collect_princeton_fulltext_expanded.py'; do
      pkill -TERM -u "$(id -u)" -f "$pat" && echo "{\"stopped\": \"$pat\"}"
    done
    touch raw/downloads_stopped_for_disk
    exit 0
  fi
  sleep 120
done
