# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/catalog_snapshot.py (sha256 790797d6d0a8c0c2966258d251f3dfce274ebe6f4722b0622872056b7bd1c37d); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Read the full-text catalog without starving the collector.

catalog.sqlite (2 GB, on NFS, rollback journal) is written by the collector, whose commits wait at most 120 s
for readers to finish. A single full-table SELECT holds a shared lock for minutes and once made a commit time
out (the collector crashed, 2026-10-17 04:32 UTC). This module reads in rowid chunks, each its own short
statement, and caches the small columns we need in cs-structure/raw/catalog_snapshot.json.gz.

snapshot(max_age_s)  -> dict(status={id: status}, doi={doi: id}, candidates={id: [url]}, attempts={id: {url: status}})
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, sqlite3, time
from pathlib import Path

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
DB = P.STORES / 'princeton/catalog.sqlite'
CACHE = STAGE / 'cs-structure/raw/catalog_snapshot.json.gz'
CHUNK = 1500


def _chunks(db, table, cols):
    hi = db.execute(f'SELECT MAX(rowid) FROM {table}').fetchone()[0] or 0
    for lo in range(0, hi + 1, CHUNK):
        rows = db.execute(f'SELECT {cols} FROM {table} WHERE rowid >= ? AND rowid < ?', (lo, lo + CHUNK)).fetchall()
        yield from rows
        time.sleep(0.05)  # let a waiting commit in between chunks


def snapshot(max_age_s=1800):
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < max_age_s:
        return json.loads(gzip.decompress(CACHE.read_bytes()))
    db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=60)
    status, doi, cands, atts = {}, {}, {}, {}
    for i, st, d in _chunks(db, 'works', 'id,status,doi'):
        status[i] = st
        if d:
            doi[d.lower()] = i
    for w, u in _chunks(db, 'candidates', 'work_id,url'):
        cands.setdefault(w, []).append(u)
    for w, u, st in _chunks(db, 'attempts', 'work_id,url,status'):
        atts.setdefault(w, {})[u] = st
    db.close()
    out = dict(taken_at=time.time(), status=status, doi=doi, candidates=cands, attempts=atts)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(gzip.compress(json.dumps(out).encode()))
    return out
