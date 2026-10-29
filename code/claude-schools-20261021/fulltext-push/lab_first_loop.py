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
import fcntl, json, signal, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

WRAPPER = str(F.P.sweep('claude-cmu-20261017') / 'tools/collector_wrapper.py')
SCRIPTS = str(F.P.HOMOGENIZING_SCRIPTS)
PY = '/usr/local/anaconda3/2024.02/bin/python'


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
    for i, d, t in F.chunks(db, 'works', 'id, doi, title'):
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


def run(out, args, label, hours=None):
    with open(out / 'loop.log', 'a') as log:
        log.write(json.dumps(dict(phase=label, started_at=F.now())) + '\n'); log.flush()
        child = subprocess.Popen(['nice', '-n', '10', PY, '-u', WRAPPER, '--out', str(out), '--skip-candidate-import', '--workers', '16'] + args,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=SCRIPTS)
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
    state(out, child_pid=None)


def main():
    school = sys.argv[1]
    hours = float(sys.argv[sys.argv.index('--full-hours') + 1]) if '--full-hours' in sys.argv else 2.0
    recent = int(sys.argv[sys.argv.index('--recent-first') + 1]) if '--recent-first' in sys.argv else None
    out = F.FT / school
    guard = open(out / '.loop.lock', 'a')
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps(dict(at=F.now(), exit='another loop holds .loop.lock')), flush=True)
        return
    rounds = 0
    while True:
        rounds += 1
        ids = lab_work_ids(school, recent)
        f = F.HERE / 'raw' / f'{school}-lab-work-ids.txt'
        f.write_text('\n'.join(ids) + '\n')
        state(out, rounds=rounds, lab_work_ids=len(ids))
        if ids:
            run(out, ['--work-ids', str(f)], f'lab_{len(ids)}')
        run(out, [], 'main', hours)
        state(out, phase='paused', child_pid=None)
        time.sleep(600)


if __name__ == '__main__':
    main()
