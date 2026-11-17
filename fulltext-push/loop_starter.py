"""Start each school's download loop once its copy-quality cache is warm (2026-11-10).

For every school still waiting, every INTERVAL seconds: stores/<s>/.copy-quality-warm.json exists, the disk-guard marker is absent, no live
`school-fulltext` job is recorded as that school's (loop-state.json slurm_job, ONE squeue per cycle), and the store's .loop.lock is free (the lock race
of 2026-11-10: a cancelled loop still held it) -> `atlas submit --test-only`, refuse on "Preempts:", then submit school-collector.slurm with
SCHOOL and CHANNELS in the environment. Each start is recorded in logs/loop-starter.json, so a restart of this job never starts a school twice.
Exits 0 when every school is started. Local file reads only; no polling faster than INTERVAL (default 60 s).
--early (R3c, 2026-11-17): a school that is still onboarding may start from its downloads-ready record (tools/downloads_ready.py: gates 0-2, a fresh build,
add_works --early run; its stage 3-8 gates may be open) instead of waiting for them. ready() then also needs that record. Without --early nothing changes.
usage: loop_starter.py [--early] <school> [<school> ...]     env LOOP_STARTER_CHANNELS (default "oa_arxiv europepmc pmc"), LOOP_STARTER_INTERVAL_S
"""
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

OPTS = ['--partition=all', '--account=mltheory', '--time=00:59:00', '--exclude=node302,node014,node805,node808']
SCRIPT = 'fulltext-push/school-collector.slurm'
MARKER = 'downloads_stopped_by_disk_guard'


def lock_free(store):
    with open(Path(store) / '.loop.lock', 'a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(f, fcntl.LOCK_UN)
        return True


def live_jobs(run=subprocess.run):
    """Ids of our running or pending school-fulltext jobs: the cycle's single squeue (None when squeue fails, so nothing starts)."""
    r = run(['squeue', '-h', '-u', os.environ.get('USER', ''), '-n', 'school-fulltext', '-o', '%i'], capture_output=True, text=True, timeout=60)
    return set(r.stdout.split()) if r.returncode == 0 else None


def loop_job_of(store):
    try:
        return str(json.loads((Path(store) / 'loop-state.json').read_text()).get('slurm_job') or '')
    except (OSError, ValueError):
        return ''


def ready(school, store, live, raw, early=False):
    """Why the school cannot start yet, or None. early: also require the school's recorded downloads-ready (add_works --early done)."""
    if early:
        import downloads_ready as DR
        why = DR.start_blocker(school)
        if why:
            return why
    if not (Path(store) / '.copy-quality-warm.json').exists():
        return 'cache not warm'
    if (Path(raw) / MARKER).exists():
        return 'disk guard marker'
    if live is None:
        return 'squeue failed'
    if loop_job_of(store) in live:
        return 'its loop job is still live'
    if not lock_free(store):
        return 'loop lock held'
    return None


SNAPSHOT_SLOTS = ('CS_ATLAS_TOOLS', 'CS_ATLAS_TESTS', 'CS_ATLAS_VENDOR', 'CS_ATLAS_SCHOOL_CONFIGS', 'CS_ATLAS_FULLTEXT_PUSH', 'CS_ATLAS_AI_WRITING')   # as loop_job.sh's _resubmit unsets them


def submit(school, channels, run=subprocess.run, code=None, extra_env=None):
    """extra_env (2026-11-16, wayback_rotate.py): variables the loop and its self-resubmits carry, e.g. WAYBACK_HOLD."""
    code = code or os.environ['CS_ATLAS_CODE']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SLURM_', 'CS_ATLAS_SNAPSHOT', 'SNAPSHOT_REPO')) and (extra_env is None or k not in SNAPSHOT_SLOTS)}   # a fresh submission of main's script, never this job's own snapshot
    env.update(SCHOOL=school, **(extra_env or {}))
    if channels:
        env.update(CHANNELS=channels, CHANNELS_FORCE='1')
    atlas = [f'{code}/bin/atlas', 'submit']
    t = run(atlas + ['--test-only'] + OPTS + [SCRIPT], capture_output=True, text=True, env=env, cwd=code, timeout=300)
    if t.returncode != 0 or 'Preempts:' in t.stdout + t.stderr:
        return None
    r = run(atlas + OPTS + [SCRIPT], capture_output=True, text=True, env=env, cwd=code, timeout=300)
    # atlas submit echoes its sbatch command (a '+ sbatch ...' trace on stderr) AFTER the sbatch line: look for the line, not the last one
    # (2026-11-10: the first run started stanford but recorded None, so a restart could have started it twice)
    for line in (r.stdout + '\n' + r.stderr).splitlines():
        if r.returncode == 0 and line.startswith('Submitted batch job '):
            return line.split()[-1]
    return None


def main(schools, early=False):
    state_file = F.P.FT_LOGS / 'loop-starter.json'
    channels = os.environ.get('LOOP_STARTER_CHANNELS', '')   # empty: the charter decides (school-collector.slurm ignores CHANNELS unless CHANNELS_FORCE=1)
    interval = int(os.environ.get('LOOP_STARTER_INTERVAL_S', '60'))
    while True:
        try:
            started = json.loads(state_file.read_text())
        except (OSError, ValueError):
            started = {}
        todo = [s for s in schools if s not in started]
        if not todo:
            print(json.dumps(dict(at=F.now(), all_started=started)), flush=True)
            return 0
        live = live_jobs()
        for s in todo:
            why = ready(s, F.FT / s, live, F.P.FT_RAW, early=early)
            if why:
                continue
            job = submit(s, channels)
            print(json.dumps(dict(at=F.now(), school=s, submitted=job)), flush=True)
            if job:
                started[s] = dict(job=job, at=F.now())
                state_file.write_text(json.dumps(started, indent=1))
                live = (live or set()) | {job}
        time.sleep(interval)


if __name__ == '__main__':
    sys.exit(main([a for a in sys.argv[1:] if a != '--early'], early='--early' in sys.argv))
