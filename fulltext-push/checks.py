"""The per-school checks store (2026-10-30, owner: every channel logs its negatives; docs/UNAVAILABLE.md).

fulltext-push/checks/<school>.sqlite, table checks(id, school, paper_key, work_id, channel, at, query, result, detail):
one row per (paper, channel) examination, result 'found' | 'none' | 'error' | 'not_applicable', detail JSON text.
Several steps write at once (run_steps.sh runs different channels side by side), so every write commits per batch of at
most 200 rows with a 120 s busy timeout and waits out a lock. Readers take the newest row per (paper_key, channel).
The store lives beside the push's code, never in a full-text store (the collectors' catalogs and other agents' stores are
not written) and never in git (.gitignore admits code and docs only).
"""
import json, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent / 'checks'
COLS = ('school', 'paper_key', 'work_id', 'channel', 'at', 'query', 'result', 'detail')
RESULTS = ('found', 'none', 'error', 'not_applicable')


def now():
    return datetime.now(timezone.utc).isoformat()


def connect(school, path=None):
    p = Path(path) if path else DIR / f'{school}.sqlite'
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(p), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    for attempt in range(30):
        try:
            db.execute('CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, school TEXT, paper_key TEXT, work_id TEXT, channel TEXT, '
                       'at TEXT, query TEXT, result TEXT, detail TEXT)')
            db.execute('CREATE INDEX IF NOT EXISTS checks_paper_channel ON checks(paper_key, channel, at)')
            db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(10)
    return db


def record(school, rows, path=None, batch=200):
    """rows: dicts with paper_key, channel, result (+ work_id, query, detail, at). Returns rows written."""
    rows = list(rows)
    if not rows:
        return 0
    db = connect(school, path)
    t = now()
    vals = []
    for r in rows:
        assert r['result'] in RESULTS, r['result']
        d = r.get('detail')
        vals.append((school, r['paper_key'], r.get('work_id'), r['channel'], r.get('at') or t,
                     r.get('query') if isinstance(r.get('query'), (str, type(None))) else json.dumps(r.get('query')),
                     r['result'], d if isinstance(d, (str, type(None))) else json.dumps(d, default=str)))
    n = 0
    for i in range(0, len(vals), batch):
        part = vals[i:i + batch]
        for attempt in range(30):
            try:
                db.executemany(f'INSERT INTO checks ({", ".join(COLS)}) VALUES (?,?,?,?,?,?,?,?)', part)
                db.commit(); n += len(part); break
            except sqlite3.OperationalError:
                db.rollback(); time.sleep(10)
        else:
            raise RuntimeError('checks store stayed locked')
    db.close()
    return n


def latest(school, path=None, channels=None):
    """{(paper_key, channel): row dict} of the newest check per paper and channel (detail parsed when JSON)."""
    p = Path(path) if path else DIR / f'{school}.sqlite'
    out = {}
    if not p.exists():
        return out
    db = sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    hi = db.execute('SELECT MAX(id) FROM checks').fetchone()[0] or 0
    for lo in range(0, hi + 1, 20000):
        for row in db.execute(f'SELECT {", ".join(COLS)} FROM checks WHERE id >= ? AND id < ? ORDER BY id', (lo, lo + 20000)).fetchall():
            r = dict(zip(COLS, row))
            if channels and r['channel'] not in channels:
                continue
            try:
                r['detail'] = json.loads(r['detail']) if r['detail'] else None
            except ValueError:
                pass
            k = (r['paper_key'], r['channel'])
            if k not in out or r['at'] >= out[k]['at']:
                out[k] = r
    db.close()
    return out


def age_days(at):
    try:
        t = datetime.fromisoformat(at)
    except (TypeError, ValueError):
        return 1e9
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 86400
