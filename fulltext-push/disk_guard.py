"""Disk guard for the full-text downloads (redesigned 2026-11-10; replaces the pkill version that watched the old share).

Every INTERVAL seconds read the free space of the project share with `df -B1G` (never du). Below LIMIT_GB it
  1. touches the stop marker raw/downloads_stopped_for_disk (the loops and their Slurm scripts refuse to start while it exists;
     loop_job.sh also refuses to resubmit), and
  2. scancels our own download jobs by NAME (scancel --name=<n> -u $USER: reaches every node, unlike pkill on one host).
A scancel is a deliberate stop: loop_job.sh does not resubmit on TERM. The guard keeps watching afterwards.
The marker is cleared by hand once space is back:  rm "$CS_ATLAS_FT_RAW/downloads_stopped_for_disk"  (the guard never removes it).
Limit 250 GB (env DISK_GUARD_LIMIT_GB): the share is 12 TB shared with every worker; the loops add a few GB an hour, a 2-minute check plus the
time a job needs to die is minutes, but other workers' stores, catalog backups, SQLite copies and checkpoint restores can take 100+ GB at once,
and a full share breaks every job on every node, so the stop must fire while that headroom still exists.
Run it as a Slurm job (fulltext-push/disk-guard.slurm, 1 CPU, 1 G, restarts itself); `disk_guard.py --once` is a single check for hand use.
log: one JSON line per action on stdout (the job's .out).
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MARKER_NAME = 'downloads_stopped_for_disk'
# our download jobs only: never another worker's jobs (Oxford, HKUST, ... run under their own names)
DEFAULT_JOB_NAMES = ('school-fulltext', 'michigan-fulltext', 'fulltext-downloads', 'fulltext-retry-transient',
                     'etd-crawl', 'etd-uc-chain', 'etd-gatech-live', 'oai-repo')
LIMIT_GB = 250
INTERVAL_S = 120


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def free_gb(path, run=subprocess.run):
    out = run(['df', '-B1G', '--output=avail', str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
    return int(out.strip().splitlines()[-1].strip())


def stop_downloads(marker, names, free, limit, run=subprocess.run, user=None):
    marker = Path(marker)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(dict(at=now(), free_gb=free, limit_gb=limit)) + '\n')
    user = user or os.environ.get('USER') or str(os.getuid())
    cancelled = {}
    for n in names:
        r = run(['scancel', f'--name={n}', '-u', user], capture_output=True, text=True, timeout=120)
        cancelled[n] = r.returncode
    return cancelled


def check(path, marker, limit=LIMIT_GB, names=DEFAULT_JOB_NAMES, run=subprocess.run):
    """One pass: returns the log record. Stops the downloads when free < limit (repeatedly, until the marker is cleared and space is back)."""
    free = free_gb(path, run)
    rec = dict(at=now(), free_gb=free, limit_gb=limit)
    if free < limit:
        rec['action'] = 'stopping downloads'
        rec['scancel'] = stop_downloads(marker, names, free, limit, run)
    return rec


def main(argv):
    from_env = os.environ.get
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent / 'tools'))
    import atlas_paths as P  # every path in one place
    path = from_env('DISK_GUARD_PATH') or str(P.ROOT)  # df of the project share
    marker = Path(P.FT_RAW) / MARKER_NAME
    limit = int(from_env('DISK_GUARD_LIMIT_GB', LIMIT_GB))
    interval = int(from_env('DISK_GUARD_INTERVAL_S', INTERVAL_S))
    names = tuple((from_env('DISK_GUARD_JOB_NAMES') or ' '.join(DEFAULT_JOB_NAMES)).split())
    while True:
        try:
            rec = check(path, marker, limit, names)
        except Exception as e:  # a failed df must not kill the guard
            rec = dict(at=now(), error=str(e)[:200])
        if 'action' in rec or 'error' in rec or '--once' in argv:
            print(json.dumps(rec), flush=True)
        if '--once' in argv:
            return 0 if 'action' not in rec else 2
        time.sleep(interval)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
