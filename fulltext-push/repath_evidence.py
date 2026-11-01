"""Repoint catalog evidence paths written before the project moves (2026-10-31).

Candidates, assets and works carry `metadata_source` (and Princeton's collection_scope, work_lab_sources and
work_coauthor_sources carry `evidence_path`, handled the same way): the evidence file a candidate came from, which the collector reads
for some downloads (a PMC copy's proof, a non-article label). Rows written before the moves still name
/n/fs/similarity/homogenizing-science/data/fulltext/<school>/..., /n/fs/resemble/homogenizing-science/data/fulltext/...,
/n/fs/resemble/cs-atlas/stores/... or /n/fs/resemble/cs-atlas-fulltext/<school>/..., none of which exist; a download that
needs the file then fails as worker_error (ENOENT). Each old prefix maps to the store's current directory
(atlas_paths STORES/<school>/); a path is rewritten only when its file exists there.

plan   distinct old paths per table, whether the mapped file exists -> review-20261030/repath-<school>.json
apply  UPDATE in rowid chunks, each under the catalog write lock (catalog_lock.py); paths whose file is missing are left
       as they are and counted. attempts.detail keeps the path an attempt saw (history) and is only counted.
usage: repath_evidence.py plan|apply <school> ...
"""
import json, sqlite3, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402

OUT = HERE / 'review-20261030'
TABLES = (('candidates', 'metadata_source'), ('assets', 'metadata_source'), ('works', 'metadata_source'),
          ('collection_scope', 'evidence_path'), ('work_lab_sources', 'evidence_path'), ('work_coauthor_sources', 'evidence_path'))


def present(db):
    """TABLES that exist in this catalog (the evidence tables only the Princeton catalog has are skipped elsewhere)."""
    have = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return [(t, c) for t, c in TABLES if t in have]


def old_prefixes(school):
    return [f'/n/fs/similarity/homogenizing-science/data/fulltext/{school}/', f'/n/fs/resemble/homogenizing-science/data/fulltext/{school}/',
            f'/n/fs/resemble/cs-atlas/stores/{school}/', f'/n/fs/resemble/cs-atlas-fulltext/{school}/']


def mapped(school, path):
    for o in old_prefixes(school):
        if path and path.startswith(o):
            return str(F.FT / school) + '/' + path[len(o):]
    return None


def chunks(db, table, col, n=20000):
    hi = db.execute(f'SELECT MAX(rowid) FROM {table}').fetchone()[0] or 0
    for lo in range(0, hi + 1, n):
        yield lo, db.execute(f"SELECT rowid, {col} FROM {table} WHERE rowid >= ? AND rowid < ? AND ({col} LIKE '/n/fs/similarity/%' OR "
                             f"{col} LIKE '/n/fs/resemble/homogenizing-science/data/%' OR {col} LIKE '/n/fs/resemble/cs-atlas%')", (lo, lo + n)).fetchall()
        time.sleep(0.02)


def plan(school):
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    out, distinct = {}, {}
    for t, col in present(db):
        n = Counter()
        for lo, rows in chunks(db, t, col):
            for rid, v in rows:
                m = mapped(school, v)
                if m is None:
                    n['unmapped_prefix'] += 1; continue
                if v not in distinct:
                    distinct[v] = Path(m).is_file()
                n['exists' if distinct[v] else 'missing'] += 1
        out[t] = dict(n)
    att = Counter()
    for lo, rows in chunks(db, 'attempts', 'detail'):
        att['attempt_details_with_old_path'] += len(rows)
    db.close()
    missing = sorted(v for v, ok in distinct.items() if not ok)
    OUT.mkdir(exist_ok=True)
    (OUT / f'repath-{school}.json').write_text(json.dumps(dict(school=school, at=F.now(), tables=out, distinct_paths=len(distinct),
                                                               missing_files=missing[:500], missing_count=len(missing), **att), indent=1))
    print(json.dumps(dict(school=school, tables=out, distinct_paths=len(distinct), missing_files=len(missing), **att)), flush=True)


def apply(school):
    store = F.FT / school
    F.backup_catalog(store, 'before-repath')
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    ok_cache, n = {}, Counter()
    for t, col in present(db):
        hi = db.execute(f'SELECT MAX(rowid) FROM {t}').fetchone()[0] or 0
        for lo in range(0, hi + 1, 5000):
            rows = db.execute(f"SELECT rowid, {col} FROM {t} WHERE rowid >= ? AND rowid < ? AND ({col} LIKE '/n/fs/similarity/%' OR "
                              f"{col} LIKE '/n/fs/resemble/homogenizing-science/data/%' OR {col} LIKE '/n/fs/resemble/cs-atlas%')", (lo, lo + 5000)).fetchall()
            ups = []
            for rid, v in rows:
                m = mapped(school, v)
                if m is None:
                    n[f'{t}:unmapped'] += 1; continue
                if v not in ok_cache:
                    ok_cache[v] = Path(m).is_file()
                if ok_cache[v]:
                    ups.append((m, rid))
                else:
                    n[f'{t}:file_missing_left'] += 1
            if ups:
                for attempt in range(30):
                    try:
                        with F.catalog_lock(store):
                            db.executemany(f'UPDATE {t} SET {col}=? WHERE rowid=?', ups)
                            db.commit()
                        break
                    except sqlite3.OperationalError:
                        db.rollback(); time.sleep(20)
                else:
                    raise RuntimeError('catalog stayed locked')
                n[f'{t}:repointed'] += len(ups)
            time.sleep(0.05)
    db.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    cmd, schools = sys.argv[1], sys.argv[2:]
    for s in schools:
        {'plan': plan, 'apply': apply}[cmd](s)
