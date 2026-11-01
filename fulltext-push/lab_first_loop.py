"""Lab papers first: a collector loop for one school's catalog that gives the CS lab papers their own pass before the
rest of the catalog (2026-10-22; the owner's full-paper analyses read the lab papers).

Each round:
  lab   the unchanged collector (scripts/collect_princeton_fulltext_expanded.py through the CMU stage's
        collector_wrapper.py: robots.txt, per-host pacing, the identity check) with --work-ids = every catalog work
        that is a lab paper (hierarchy/<school>/lab_papers.jsonl.gz) without a copy: its own work and any catalog work
        with the same DOI or normalized title (the coverage counter's rule)
  full  the same collector on the whole catalog, stopped after FULL_HOURS so new lab candidates wait at most that long
        (a stopped pass loses nothing: tried URLs are recorded per work, the rest stay untried for the next pass)
  pause 10 minutes
It holds data/fulltext/<school>/.loop.lock, the lock claude-berkeley-20261021/tools/bk_collect_loop.py takes, so the
two never run together. State -> data/fulltext/<school>/loop-state.json, log -> loop.log (as bk_collect_loop.py).
--recent-first Y (2026-10-27, Stanford): the lab pass's --work-ids list puts lab papers from year Y on first (the collector
works through a --work-ids list in its order within each host); without it the order is unchanged.
usage: lab_first_loop.py <school> [--full-hours H] [--recent-first Y]
"""
import fcntl, json, os, signal, socket, sqlite3, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

WRAPPER = str(F.P.vendor('cmu_tools') / 'collector_wrapper.py')  # vendored 2026-10-30 (tools/vendor_sync.py)
SCRIPTS = str(F.P.vendor('homogenizing_scripts'))  # the collector's directory (its cwd)
PY = str(F.P.COLLECTOR_PY)


def state(out, **kw):
    p = out / 'loop-state.json'
    try:
        s = json.loads(p.read_text())
    except Exception:
        s = {}
    s.update(kw, updated_at=F.now(), loop='fulltext-push/lab_first_loop.py'); p.write_text(json.dumps(s, indent=1))


def lab_work_ids(school, recent_first=None):
    papers = F.lab_papers(school)
    cs = F.catalog_state(school, with_urls=False)
    ids = []
    import sqlite3
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    doi_ids, title_ids = {}, {}
    for i, d, t in F.works_rows(db, 'id, doi, title'):  # the works_slim covering index when present (2026-10-29)
        if d:
            doi_ids.setdefault(F.ndoi(d), []).append(i)
        k = F.nt(t)
        if len(k) >= 20:
            title_ids.setdefault(k, []).append(i)
    db.close()
    later = []
    for r in papers.values():
        if F.is_local(school, r, cs):
            continue
        w = F.match_work(school, r, cs)
        group = ([w] if w else []) + doi_ids.get(F.ndoi(r.get('doi')), []) + title_ids.get(F.nt(r.get('title')), [])
        group = [i for i in group if cs['status'].get(i) not in F.LOCAL]
        if recent_first and (r.get('year') or 0) < recent_first:
            later += group
        else:
            ids += group
    return list(dict.fromkeys(ids + later))


# Supervision (ROADMAP item 12, 2026-10-31): the loop runs as a Slurm job (fulltext-push/downloads.slurm). SIGTERM (scancel,
# the job's time limit) stops it cleanly: the running collector gets SIGTERM (a stopped pass loses nothing: tried URLs
# are recorded per work), the state says 'stopped', the lock is released. A round that made no new attempt counts as
# idle and the pause doubles (10 min up to 4 h) instead of spinning; any attempt resets it. After every round the status
# page is regenerated (collectors_status.py -> hierarchy/COLLECTORS-STATUS.md).
STOP = {'flag': False, 'child': None}


def _on_term(signum, frame):
    STOP['flag'] = True
    c = STOP['child']
    if c is not None and c.poll() is None:
        c.send_signal(signal.SIGTERM)


def max_attempt(out):
    try:
        db = sqlite3.connect(f'file:{out / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
        v = db.execute('SELECT MAX(id) FROM attempts').fetchone()[0] or 0
        db.close()
        return v
    except sqlite3.Error:
        return None


def sleep_unless_stopped(seconds):
    end = time.monotonic() + seconds
    while not STOP['flag'] and time.monotonic() < end:
        time.sleep(min(15, end - time.monotonic()))


def run(out, args, label, hours=None):
    if STOP['flag']:
        return
    with open(out / 'loop.log', 'a') as log:
        log.write(json.dumps(dict(phase=label, started_at=F.now())) + '\n'); log.flush()
        child = subprocess.Popen(['nice', '-n', '10', PY, '-u', WRAPPER, '--out', str(out), '--skip-candidate-import', '--workers', '16'] + args,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=SCRIPTS)
        STOP['child'] = child
        state(out, phase=label, started=F.now(), child_pid=child.pid)
        try:
            code = child.wait(timeout=hours * 3600 if hours else None)
        except subprocess.TimeoutExpired:
            child.send_signal(signal.SIGTERM)
            try:
                code = child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                child.kill(); code = child.wait()
            code = f'stopped after {hours} h (SIGTERM {code})'
        log.write(json.dumps(dict(phase=label, finished_at=F.now(), exit=code)) + '\n')
    STOP['child'] = None
    state(out, child_pid=None)


def main():
    school = sys.argv[1]
    hours = float(sys.argv[sys.argv.index('--full-hours') + 1]) if '--full-hours' in sys.argv else 2.0
    recent = int(sys.argv[sys.argv.index('--recent-first') + 1]) if '--recent-first' in sys.argv else None
    out = F.FT / school
    import store_layout  # the store's directories first: a collector without sources/ fails every attempt (2026-10-31)
    made = store_layout.ensure(out)
    if made:
        print(json.dumps(dict(at=F.now(), store_layout_created=made)), flush=True)
    guard = open(out / '.loop.lock', 'a')
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps(dict(at=F.now(), exit='another loop holds .loop.lock')), flush=True)
        return
    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)
    job = os.environ.get('SLURM_JOB_ID')
    if os.environ.get('SLURM_ARRAY_JOB_ID'):
        job = f"{os.environ['SLURM_ARRAY_JOB_ID']}_{os.environ.get('SLURM_ARRAY_TASK_ID')}"
    state(out, slurm_job=job, host=socket.gethostname(), pid=os.getpid(), python=PY, wrapper=WRAPPER, idle_rounds=0)
    rounds, idle = 0, 0
    while not STOP['flag']:
        rounds += 1
        before = max_attempt(out)
        ids = lab_work_ids(school, recent)
        f = F.P.FT_RAW / f'{school}-lab-work-ids.txt'
        f.write_text('\n'.join(ids) + '\n')
        state(out, rounds=rounds, lab_work_ids=len(ids))
        if ids:
            run(out, ['--work-ids', str(f)], f'lab_{len(ids)}')
        run(out, [], 'main', hours)
        after = max_attempt(out)
        idle = idle + 1 if (before is not None and after == before) else 0
        pause = min(600 * 2 ** idle, 4 * 3600)
        state(out, phase='stopped' if STOP['flag'] else 'paused', child_pid=None, idle_rounds=idle, next_round_in_s=0 if STOP['flag'] else pause)
        try:
            import collectors_status
            collectors_status.main()
        except Exception as e:  # the status page must never stop the loop
            print(json.dumps(dict(at=F.now(), status_page_failed=str(e)[:200])), flush=True)
        sleep_unless_stopped(pause)
    state(out, phase='stopped', child_pid=None, stopped_at=F.now())
    print(json.dumps(dict(at=F.now(), exit='stopped on SIGTERM', rounds=rounds)), flush=True)


if __name__ == '__main__':
    main()
