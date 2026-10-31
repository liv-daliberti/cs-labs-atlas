"""Quarantine local lab-paper copies taken from paths whose robots.txt disallows an Anthropic crawler (2026-10-31, owner).

The owner's rule: never bypass a robots.txt rule, including rules naming ClaudeBot or anthropic-ai. The collector checked
robots.txt for its own user agent only until 2026-10-30 (collector_wrapper.py now also obeys the groups below); copies it
took from paths disallowed for these agents no longer count.

plan   every local catalog work a lab paper counts by the coverage counter's rule (the paper's catalog work, and any
       local work with its DOI or normalized title): its download URL (works.download_url, the final URL after
       redirects) and the URL of its 'downloaded' attempt (the candidate it started from) against each host's
       robots.txt (fetched once per host, redirects followed, as the collector does). A copy is flagged when a URL is
       allowed for the collector's own user agent but disallowed for one of AI_AGENTS.
       -> fulltext-push/review-20261030/robots-ai-quarantine-plan-<school>.json
apply  per flagged work, one short transaction: the file moves (os.rename, never deleted) to
       <store>/quarantine/robots-ai/<its relative path> (a file another local, unflagged work also uses stays where it is
       and only the flagged work is marked); works.status -> 'quarantined_robots_ai' (not a copy for the counter, and
       the collector may still try the work's other candidates), works.file_path and assets.path -> the quarantine
       path; the work's by_lab symlink is removed. Manifest (work id, original path, new path, sha256, URLs, rule
       matched) -> <store>/quarantine/robots-ai/manifest.jsonl, so every step can be reversed (restore).
restore <school> moves the files back and restores status / paths from the manifest.
usage: quarantine_robots_ai.py plan|apply <school> ...
       quarantine_robots_ai.py restore <school> [--dry-run] [--only <work id>,<work id>]
"""
import json, os, re, sqlite3, sys, time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402

AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')
STATUS = 'quarantined_robots_ai'
PLAN = HERE / 'review-20261030'
AUDITED = {h for h, v in json.loads((PLAN / 'ai-robots-audit.json').read_text()).items() if v.get('ai_disallowed')} \
    if (PLAN / 'ai-robots-audit.json').exists() else set()


def host(u):
    return (urlsplit(u or '').hostname or '').lower()


class Robots:
    def __init__(self):
        import requests
        self.s = requests.Session(); self.s.headers['User-Agent'] = F.UA; self.s.trust_env = False
        self.rules, self.texts = {}, {}

    def get(self, h):
        if h not in self.rules:
            from protego import Protego
            time.sleep(0.3)
            try:
                r = self.s.get(f'https://{h}/robots.txt', timeout=(10, 25))
                txt = '' if r.status_code == 404 else (r.text if r.status_code == 200 else None)
            except Exception:
                txt = None
            self.texts[h] = txt
            self.rules[h] = Protego.parse(txt) if txt is not None else None
        return self.rules[h]

    def verdict(self, url):
        """None (allowed for every agent) or the AI agent the URL is disallowed for. A robots.txt unreadable now (bioRxiv
        answered HTTP 429 on 2026-10-31) falls back to the host-level audit of 2026-10-30, which read it then
        (review-20261030/ai-robots-audit.json: every copy from the host was on a path disallowed for an AI agent)."""
        h = host(url)
        p = self.get(h)
        if p is None:
            return 'audit-2026-10-30 (robots.txt unreadable now)' if h in AUDITED else None
        if not p.can_fetch(url, F.UA):
            return None
        for a in AI_AGENTS:
            if not p.can_fetch(url, a):
                return a
        return None


def lab_local_works(school):
    """{work id: row} of the local catalog works that make lab papers local by the counter's rule."""
    copies = json.loads((F.SCHOOLS / 'hierarchy' / school / 'copies.json').read_text())['papers']
    papers = F.lab_papers(school)
    cids = {c['catalog'] for c in copies.values() if c.get('catalog')}
    dois = {F.ndoi(r.get('doi')) for r in papers.values()} - {''}
    titles = {re.sub(r'[^a-z0-9]', '', (r.get('title') or '').lower()) for r in papers.values()} - {''}
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    keep = set()
    for i, d, s, t in F.works_rows(db, 'id, doi, status, title'):
        if s in F.LOCAL and (i in cids or F.ndoi(d) in dois or re.sub(r'[^a-z0-9]', '', (t or '').lower()) in titles):
            keep.add(i)
    rows = {}
    ids = sorted(keep)
    for k in range(0, len(ids), 500):
        part = ids[k:k + 500]
        q = ','.join('?' * len(part))
        for i, fp, sha, du, st, yr in db.execute(f'SELECT id, file_path, sha256, download_url, status, year FROM works WHERE id IN ({q})', part):
            rows[i] = dict(id=i, file_path=fp, sha256=sha, download_url=du, status=st, year=yr, attempt_urls=[])
        for w, u in db.execute(f"SELECT work_id, url FROM attempts WHERE work_id IN ({q}) AND status IN ('downloaded','fulltext_xml')", part):
            rows[w]['attempt_urls'].append(u)
    db.close()
    return rows


def plan(school, robots):
    rows = lab_local_works(school)
    flagged, n = [], Counter()
    for w, r in rows.items():
        urls = list(dict.fromkeys([u for u in [r['download_url']] + r['attempt_urls'] if u]))
        hit = None
        for u in urls:
            a = robots.verdict(u)
            if a:
                hit = dict(url=u, agent=a, host=host(u)); break
        n['checked'] += 1
        if hit:
            flagged.append(dict(r, rule=hit)); n['flagged'] += 1; n['host:' + hit['host']] += 1
    PLAN.mkdir(exist_ok=True)
    out = PLAN / f'robots-ai-quarantine-plan-{school}.json'
    out.write_text(json.dumps(dict(school=school, at=F.now(), agents=AI_AGENTS, local_lab_works=len(rows), flagged=flagged), indent=0))
    top = Counter({k[5:]: v for k, v in n.items() if k.startswith('host:')}).most_common(8)
    print(json.dumps(dict(school=school, local_lab_works=len(rows), flagged=n['flagged'], top_hosts=dict(top))), flush=True)


def apply(school):
    store = F.FT / school
    p = json.loads((PLAN / f'robots-ai-quarantine-plan-{school}.json').read_text())
    qdir = store / 'quarantine' / 'robots-ai'
    qdir.mkdir(parents=True, exist_ok=True)
    flagged = {x['id'] for x in p['flagged']}
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    # files another local, unflagged work also uses stay in place
    shared = set()
    fps = sorted({x['file_path'] for x in p['flagged'] if x['file_path']})
    for k in range(0, len(fps), 500):
        part = fps[k:k + 500]
        for i, fp in db.execute(f"SELECT id, file_path FROM works WHERE file_path IN ({','.join('?' * len(part))}) AND status IN ('downloaded','fulltext_xml')", part):
            if i not in flagged:
                shared.add(fp)
    n = Counter()
    man = open(qdir / 'manifest.jsonl', 'a')
    for x in p['flagged']:
        w, fp = x['id'], x['file_path']
        cur = db.execute('SELECT status, file_path FROM works WHERE id=?', (w,)).fetchone()
        if not cur or cur[0] not in F.LOCAL or cur[1] != fp:
            n['skipped_changed'] += 1; continue
        moved, new = False, fp
        if fp and fp not in shared and (store / fp).exists():
            new = str(Path('quarantine') / 'robots-ai' / fp)
            (store / new).parent.mkdir(parents=True, exist_ok=True)
            os.rename(store / fp, store / new); moved = True
        for attempt in range(30):
            try:
                with F.catalog_lock(store):  # one writer per catalog
                    db.execute('UPDATE works SET status=?, file_path=? WHERE id=?', (STATUS, new, w))
                    db.execute('UPDATE assets SET path=? WHERE work_id=? AND path=?', (new, w, fp))
                    db.commit()
                break
            except sqlite3.OperationalError:
                db.rollback(); time.sleep(10)
        else:
            if moved:
                os.rename(store / new, store / fp)
            raise RuntimeError('catalog stayed locked')
        links = []
        for link in (store / 'by_lab').glob(f"*/{x['year']}--{w}.*"):
            if link.is_symlink():
                links.append(dict(link=str(link), target=os.readlink(link))); link.unlink()
        man.write(json.dumps(dict(at=F.now(), school=school, work_id=w, old_status=cur[0], status=STATUS, original_path=fp, quarantine_path=new,
                                  moved=moved, shared_file=fp in shared, sha256=x['sha256'], download_url=x['download_url'],
                                  attempt_urls=x['attempt_urls'], rule=x['rule'], by_lab_links=links,
                                  by='fulltext-push/quarantine_robots_ai.py')) + '\n')
        man.flush()
        n['quarantined'] += 1; n['moved'] += moved
    man.close(); db.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


def restore(school, dry=False, only=None):
    """Undo apply from the manifest: the file back to its original path, status and paths restored, the by_lab link
    re-made. dry: check and print what would happen, change nothing. only: these work ids."""
    store = F.FT / school
    qdir = store / 'quarantine' / 'robots-ai'
    db = sqlite3.connect(f'file:{store / "catalog.sqlite"}?mode=ro', uri=True, timeout=120) if dry else sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    n = Counter()
    for line in open(qdir / 'manifest.jsonl'):
        m = json.loads(line)
        if m.get('restored') or (only and m['work_id'] not in only):
            continue
        if dry:
            st, fp = db.execute('SELECT status, file_path FROM works WHERE id=?', (m['work_id'],)).fetchone()
            q = store / m['quarantine_path']
            ok = st == STATUS and fp == m['quarantine_path'] and (not m['moved'] or (q.exists() and not (store / m['original_path']).exists()))
            if m['moved'] and q.exists():
                import hashlib
                ok = ok and hashlib.sha256(q.read_bytes()).hexdigest() == m['sha256']
            print(json.dumps(dict(work=m['work_id'], would=dict(rename=[m['quarantine_path'], m['original_path']] if m['moved'] else None,
                                                                    status=[st, m['old_status']], file_path=[fp, m['original_path']],
                                                                    by_lab_links=[l['link'] for l in m.get('by_lab_links') or []]), checks_ok=ok)))
            n['dry_ok' if ok else 'dry_problem'] += 1
            continue
        if m['moved'] and (store / m['quarantine_path']).exists():
            os.rename(store / m['quarantine_path'], store / m['original_path'])
        db.execute('UPDATE works SET status=?, file_path=? WHERE id=? AND status=?', (m['old_status'], m['original_path'], m['work_id'], STATUS))
        db.execute('UPDATE assets SET path=? WHERE work_id=? AND path=?', (m['original_path'], m['work_id'], m['quarantine_path']))
        db.commit()
        for l in m.get('by_lab_links') or []:
            if not os.path.lexists(l['link']):
                os.symlink(l['target'], l['link'])
        n['restored'] += 1
    db.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    argv = sys.argv[1:]
    only = None
    if '--only' in argv:
        i = argv.index('--only'); only = set(argv[i + 1].split(',')); argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    cmd, schools = args[0], args[1:]
    rb = Robots() if cmd == 'plan' else None
    for s in schools:
        {'plan': lambda s: plan(s, rb), 'apply': apply, 'restore': lambda s: restore(s, '--dry-run' in sys.argv, only)}[cmd](s)
    if rb:  # the robots.txt texts the plan read: the evidence for every flag
        (PLAN / 'robots-ai-quarantine-robots.json').write_text(json.dumps(dict(at=F.now(), texts=rb.texts)))
