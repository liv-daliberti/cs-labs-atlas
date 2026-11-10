#!/bin/sh
# One disk check by hand (2026-11-10 redesign): the watcher is a Slurm job, fulltext-push/disk-guard.slurm; see disk_guard.py for the rule.
# usage: disk_guard.sh        -> exit 0 when free space is above the limit, 2 (and the downloads stopped) when under it
cd "$(dirname "$0")"
. ../paths.sh || exit 1
exec "${CS_ATLAS_PY:-python3}" -I disk_guard.py --once
