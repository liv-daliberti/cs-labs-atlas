"""Requeue lab papers whose failed URLs failed for given access-review causes, after a collector fix that changes that
outcome (2026-10-30). Same mechanism as review_access.py apply / collector_wrapper.requeue: the (work, URL) pair's
attempt rows are deleted (each kept in <store>/staged/requeued-attempts.jsonl with requeued_by=<tag>) and a
needs_access_review work goes back to 'queued'; the running lab_first_loop collector asks again on its next round.

Selection: lab-paper works without a copy (lab_first_loop.lab_work_ids: the counter's rule) at status queued or
needs_access_review; a URL qualifies when every one of its attempts has a cause in --causes (review_access.cause), its
host is not in --exclude-hosts, and the pair was never requeued under the same tag (one retry per fix). Writes commit per
200 rows with a 120 s busy timeout (the collectors share the catalog).
usage: requeue_causes.py <school> (--causes c1,c2 | --attempt-status S [--detail-contains T]) --tag <name> [--exclude-hosts h1,h2] [--hosts h1,h2] [--max-attempts N] [--redirect-rule] [--dry]
"""
import argparse, json, sqlite3, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402
from review_access import cause, host  # noqa: E402
from lab_first_loop import lab_work_ids  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('school'); ap.add_argument('--causes', default=''); ap.add_argument('--tag', required=True)
    ap.add_argument('--attempt-status', default=None, help="instead of --causes: attempts with this status (e.g. worker_error)")
    ap.add_argument('--detail-contains', default=None, help='with --attempt-status: and this text in the detail')
    ap.add_argument('--exclude-hosts', default=''); ap.add_argument('--hosts', default='')
    ap.add_argument('--max-attempts', type=int, default=3); ap.add_argument('--dry', action='store_true')
    ap.add_argument('--redirect-rule', action='store_true', help='unapproved_redirect URLs only when collector_wrapper.redirect_ok now approves the target')
    a = ap.parse_args()
    causes = set(a.causes.split(','))
    excl = set(filter(None, a.exclude_hosts.split(',')))
    only = set(filter(None, a.hosts.split(',')))
    store = F.FT / a.school
    ids = set(lab_work_ids(a.school))
    ro = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    st = {}
    for i, s in F.works_rows(ro, 'id, status'):
        if i in ids:
            st[i] = s
    att = defaultdict(list)
    for row in F.chunks(ro, 'attempts', 'id, work_id, url, observed_at, status, detail', n=20000):
        if row[1] in ids:
            att[(row[1], row[2])].append(dict(id=row[0], work_id=row[1], url=row[2], observed_at=row[3], status=row[4], detail=row[5]))
    ro.close()
    prior = set()
    log = store / 'staged' / 'requeued-attempts.jsonl'
    if log.exists():
        for line in log.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('requeued_by') == a.tag:
                prior.add((r.get('work_id'), r.get('url')))
    plan, n = defaultdict(list), Counter()
    for (w, u), rows in att.items():
        if st.get(w) not in ('queued', 'needs_access_review') or (w, u) in prior:
            continue
        h = host(u)
        if h in excl or (only and h not in only) or len(rows) > a.max_attempts:
            continue
        if a.attempt_status:  # a collector fault, not an access outcome (2026-10-31: Michigan's store lacked sources/)
            if all(r['status'] == a.attempt_status and (a.detail_contains or '') in (r['detail'] or '') for r in rows):
                plan[w].append(rows); n['urls'] += 1; n['host:' + h] += 1
            continue
        cs = {cause(r)[0] for r in rows}
        if a.redirect_rule and 'unapproved_redirect' in cs:
            import re as _re
            sys.path.insert(0, str(F.CMU_TOOLS))
            from collector_wrapper import redirect_ok
            tg = {(_re.match(r'Redirect or URL outside the evidence-approved public hosts: (\S+)', r['detail'] or '') or [None, None])[1] for r in rows}
            if not all(t and redirect_ok(h, t) for t in tg):
                continue
        if cs and cs <= causes:
            plan[w].append(rows); n['urls'] += 1; n['host:' + h] += 1
    n['works'] = len(plan)
    print(json.dumps(dict(school=a.school, tag=a.tag, dry=a.dry, works=n['works'], urls=n['urls'],
                          top_hosts=dict(Counter({k[5:]: v for k, v in n.items() if k.startswith('host:')}).most_common(15)))), flush=True)
    if a.dry or not plan:
        return
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    items = list(plan.items())
    done = Counter()
    with log.open('a') as lf:
        for i in range(0, len(items), 200):
            part = items[i:i + 200]
            for attempt in range(30):
                try:
                  with F.catalog_lock(store):  # one writer per catalog
                    recs = []
                    for w, groups in part:
                        for rows in groups:
                            ids_ = [r['id'] for r in rows]
                            db.execute(f"DELETE FROM attempts WHERE id IN ({','.join('?' * len(ids_))}) AND work_id=?", ids_ + [w])
                            recs += rows
                        done['requeued_works'] += db.execute("UPDATE works SET status='queued' WHERE id=? AND status='needs_access_review'", (w,)).rowcount
                    db.commit()
                  break
                except sqlite3.OperationalError:
                    db.rollback(); time.sleep(20)
            else:
                raise RuntimeError('catalog stayed locked')
            for r in recs:
                lf.write(json.dumps(dict(r, requeued_at=F.now(), requeued_by=a.tag)) + '\n')
            lf.flush(); done['attempts_removed'] += len(recs)
            time.sleep(0.3)
    db.close()
    print(json.dumps(dict(school=a.school, tag=a.tag, **done)), flush=True)


if __name__ == '__main__':
    main()
