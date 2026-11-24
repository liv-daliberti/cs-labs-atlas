"""hdl_requeue: ask hdl.handle.net URLs again after the owner-approved redirect rule (2026-11-17).

The rule (vendor/cmu_tools/collector_wrapper.py: redirect_ok + seed_handle_robots): a Handle URL is followed only to the repository host it
resolves to (not a publisher, not a login host), that host's robots.txt is read once without following redirects (200 -> its rules; 404 or another
4xx that is not 401/403/429 -> no rules; anything else -> the collector's own handling), and the ClaudeBot / anthropic-ai groups apply. 429
cooldowns are untouched.

Which attempts are now stale (pair = work + hdl.handle.net URL, every attempt row of the pair must be one of these):
  unapproved_redirect  'Redirect or URL outside the evidence-approved public hosts: <host>' where redirect_ok('hdl.handle.net', host) is true now
  robots_error         the resolved host's robots.txt answered an HTTP 4xx other than 401/403/429 (the old code paused the host: 'robots.txt' in
                       the detail, review_access cause robots_unavailable)
  retired_page_rule    'DSpace@MIT web page not fetched' (a wrapper rule of 2026-10-23..27 that no longer exists)
Works are non-local only (status needs_access_review or queued). The pair's attempt rows are deleted (each kept in
<store>/staged/requeued-attempts.jsonl with requeued_by=<tag>), a needs_access_review work goes back to 'queued'; a pair is requeued once per tag.
Nothing else in the catalog is touched. Writes: fresh school-named backup (queued_oa_fill.check_backup), catalog write lock wait, <= 200 works per
transaction, integrity_check.
usage: hdl_requeue.py plan <school>[,...] [--out PLAN.json]
       hdl_requeue.py apply <school>[,...] --plan PLAN.json --backup-dir DIR [--tag hdl-redirect-20261117] [--lock-wait 2700]
"""
import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

sys.path.insert(0, str(F.CMU_TOOLS))
TAG = 'hdl-redirect-20261117'
OUTSIDE = re.compile(r'Redirect or URL outside the evidence-approved public hosts: (\S+)')
ROBOTS_4XX = re.compile(r'\b(4\d\d) Client Error.*robots\.txt')
STATES = ('needs_access_review', 'queued')


def is_hdl(url):
    from urllib.parse import urlsplit
    return (urlsplit(url or '').hostname or '').lower() == 'hdl.handle.net'


def stale_class(row, redirect_ok):
    """The stale class of one attempt row (dict with detail, url), or None."""
    d = row.get('detail') or ''
    m = OUTSIDE.match(d)
    if m:
        return 'unapproved_redirect' if redirect_ok('hdl.handle.net', m.group(1)) else None
    m = ROBOTS_4XX.search(d)
    if m and int(m.group(1)) not in (401, 403, 429):
        return 'robots_error'
    if d.startswith('DSpace@MIT web page not fetched'):
        return 'retired_page_rule'
    return None


def plan_school(school, path=None, redirect_ok=None):
    """{work id: [attempt ids]} and Counter, read-only; also the classes."""
    if redirect_ok is None:
        from collector_wrapper import redirect_ok
    path = path or F.FT / school / 'catalog.sqlite'
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    try:
        st = {r[0]: r[1] for r in db.execute(f"SELECT id, status FROM works WHERE status IN ({','.join('?' * len(STATES))})", STATES)}
        pairs = defaultdict(list)
        for a in db.execute("SELECT id, work_id, url, status, detail FROM attempts WHERE url LIKE '%hdl.handle.net/%'"):
            if a['work_id'] in st and is_hdl(a['url']):
                pairs[(a['work_id'], a['url'])].append(dict(a))
    finally:
        db.close()
    prior = set()
    log = F.FT / school / 'staged' / 'requeued-attempts.jsonl'
    if log.exists():
        for line in log.open(errors='replace'):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('requeued_by') == TAG:
                prior.add((r.get('work_id'), r.get('url')))
    plan, n = defaultdict(list), Counter()
    for (w, u), rows in pairs.items():
        if (w, u) in prior:
            continue
        cls = [stale_class(r, redirect_ok) for r in rows]
        if cls and all(cls):
            plan[w] += [r['id'] for r in rows]
            for c in set(cls):
                n['pairs_' + c] += 1
    n['works'] = len(plan)
    n['needs_access_review'] = sum(st[w] == 'needs_access_review' for w in plan)
    n['queued'] = len(plan) - n['needs_access_review']
    n['attempts'] = sum(len(v) for v in plan.values())
    return dict(plan), n


def apply_school(school, ids_by_work, backup_dir, tag=TAG, lock_wait=2700):
    import queued_oa_fill as Q
    Q.check_backup(school, backup_dir)
    Q.check_no_writer(school, lock_wait, 15)
    Q.check_backup(school, backup_dir)
    store = F.FT / school
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    db.row_factory = sqlite3.Row
    items = list(ids_by_work.items())
    n = Counter()
    (store / 'staged').mkdir(exist_ok=True)
    with (store / 'staged' / 'requeued-attempts.jsonl').open('a') as lf:
        for i in range(0, len(items), 200):
            part = items[i:i + 200]
            for _try in range(30):
                try:
                    with F.catalog_lock(store):
                        recs = []
                        for w, ids in part:
                            cur = db.execute('SELECT status FROM works WHERE id=?', (w,)).fetchone()
                            if not cur or cur['status'] not in STATES:
                                n['skipped_status_changed'] += 1
                                continue
                            q = ','.join('?' * len(ids))
                            rows = [dict(r) for r in db.execute(f'SELECT * FROM attempts WHERE id IN ({q}) AND work_id=?', ids + [w])]
                            db.execute(f'DELETE FROM attempts WHERE id IN ({q}) AND work_id=?', ids + [w])
                            recs += rows
                            n['requeued_works'] += db.execute("UPDATE works SET status='queued' WHERE id=? AND status='needs_access_review'", (w,)).rowcount
                        db.commit()
                    break
                except sqlite3.OperationalError:
                    db.rollback()
                    time.sleep(20)
            else:
                raise RuntimeError('catalog stayed locked')
            for r in recs:
                lf.write(json.dumps(dict(r, requeued_at=F.now(), requeued_by=tag)) + '\n')
            lf.flush()
            n['attempts_removed'] += len(recs)
            time.sleep(0.3)
    db.close()
    n['integrity'] = Q.integrity_ok(school)
    return dict(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['plan', 'apply'])
    ap.add_argument('schools')
    ap.add_argument('--out')
    ap.add_argument('--plan')
    ap.add_argument('--backup-dir')
    ap.add_argument('--tag', default=TAG)
    ap.add_argument('--lock-wait', type=int, default=2700)
    a = ap.parse_args(argv)
    schools = a.schools.split(',')
    if a.cmd == 'plan':
        out = {}
        for s in schools:
            plan, n = plan_school(s)
            out[s] = dict(counts=dict(n), works=plan)
            print(json.dumps(dict(at=F.now(), school=s, step='hdl_requeue_plan', **n)), flush=True)
        if a.out:
            Path(a.out).write_text(json.dumps(out))
        return
    saved = json.loads(Path(a.plan).read_text())
    for s in schools:
        res = apply_school(s, saved.get(s, {}).get('works', {}), a.backup_dir, a.tag, a.lock_wait)
        print(json.dumps(dict(at=F.now(), school=s, step='hdl_requeue_apply', **res)), flush=True)


if __name__ == '__main__':
    main()
