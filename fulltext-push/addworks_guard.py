"""Safety wrapper around add_works.py for a bulk catalog add (2026-11-10): `before <school>` takes a locked catalog backup (nothing pruned: keep=99), records its sha256, the
works count and the set of work ids; `after <school>` checks that every earlier work id is still there (no removals) and reports how many were added. add_works only
INSERT OR IGNOREs queued works and nodes, so an existing row cannot change; the id check is the proof. State: <GUARD_DIR>/<school>.before.json (+ ids .gz).
usage: addworks_guard.py before|after <school> ...     env GUARD_DIR (default scratch/downloads-1110/addworks under the project root)
"""
import gzip
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402


def guard_dir():
    d = Path(os.environ.get('GUARD_DIR') or F.P.ROOT / 'scratch' / 'downloads-1110' / 'addworks')
    d.mkdir(parents=True, exist_ok=True)
    return d


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def work_ids(path):
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    try:
        return {r[0] for r in db.execute('SELECT id FROM works')}
    finally:
        db.close()


def before(school):
    store = F.FT / school
    bk = F.backup_catalog(store, 'before-addworks-1110', keep=99)
    ids = work_ids(bk)
    g = guard_dir()
    with gzip.open(g / f'{school}.ids.gz', 'wt') as f:
        f.write('\n'.join(sorted(ids)))
    rec = dict(school=school, backup=str(bk), backup_sha256=sha256(bk), works_before=len(ids), at=F.now())
    (g / f'{school}.before.json').write_text(json.dumps(rec))
    print(json.dumps(rec), flush=True)


def after(school):
    g = guard_dir()
    rec = json.loads((g / f'{school}.before.json').read_text())
    old = set(gzip.open(g / f'{school}.ids.gz', 'rt').read().split('\n')) - {''}   # an empty catalog saves an empty file: not an id
    now = work_ids(F.FT / school / 'catalog.sqlite')
    out = dict(school=school, works_before=rec['works_before'], works_after=len(now), added=len(now - old), removed=len(old - now), backup=rec['backup'],
               backup_sha256=rec['backup_sha256'], backup_sha256_now=sha256(rec['backup']), ok=not (old - now))
    out['backup_unchanged'] = out['backup_sha256'] == out['backup_sha256_now']
    print(json.dumps(out), flush=True)
    return 0 if out['ok'] and out['backup_unchanged'] else 1


if __name__ == '__main__':
    cmd, rc = sys.argv[1], 0
    for s in sys.argv[2:]:
        if cmd == 'before':
            before(s)
        else:
            rc = max(rc, after(s))
    sys.exit(rc)
