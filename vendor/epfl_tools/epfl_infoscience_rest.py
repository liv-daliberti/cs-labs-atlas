# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-epfl-20261019/tools/epfl_infoscience_rest.py (sha256 432e22ab120e7e59142de4be356b618889bc79ccda2cdbfd38a56fdacb84f79e); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Infoscience files the OAI harvest did not turn into candidates, for EPFL catalog works without a local copy.

tools/epfl_infoscience.py took file links from MARC 856 (OAI marcxml); many records carry an ORIGINAL PDF that MARC
does not list (a 2018 thesis, EPFL_TH8502.pdf; publisher PDFs deposited by the lab), so 1,482 study-set works had only an
Infoscience handle page, which the collector does not fetch (tools/../../claude-cmu-20261017/tools/collector_wrapper.py:
Infoscience files come through the REST API). This pass asks the REST API (robots.txt allows /server/api) for the
handles the works already cite:

  resolve  /server/api/pid/find?id=hdl:<handle> (redirects to the item), then /server/api/core/items/<uuid>/bundles
           ?embed=bitstreams: the ORIGINAL bundle's files. One request per 3 s (as tools/epfl_web.py); an empty HTTP 202
           (the site's bot challenge), 429 or 503 stops the pass for 10 minutes and is never worked around. Cached in
           raw/infoscience_rest.jsonl (resumable; failures asked again).
  add      every ORIGINAL file named *.pdf (<= 500 MiB) becomes the candidate
           https://infoscience.epfl.ch/server/api/core/bitstreams/<uuid>/content (redirects to the signed file store
           approved in the collector wrapper). Files EPFL restricts answer 401/403 there and stay unavailable; nothing is
           worked around. The handle comes from the work's own candidates; the collector's title check applies.
Evidence -> data/fulltext/epfl/discovery/claude-epfl-catalog/evidence/infoscience-rest-<stamp>.json.
usage: epfl_infoscience_rest.py [resolve] [add] [--first <missing_epfl.json>] [--batch N]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-epfl-20261019'  # vendored: the data root (was Path(__file__).resolve().parents[1])
OUT = P.STORES / 'epfl'
CACHE = STAGE / 'raw' / 'infoscience_rest.jsonl'
API = 'https://infoscience.epfl.ch/server/api'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
HANDLE = re.compile(r'^https?://(?:infoscience\.epfl\.ch/(?:handle/)?|hdl\.handle\.net/)(20\.500\.14299/\d+)(?:[/?#]|$)')
LIMIT = 500 * 1024 * 1024


def chunks(db, table, cols, n=20000):
    hi = db.execute(f'SELECT MAX(rowid) FROM {table}').fetchone()[0] or 0
    for lo in range(0, hi + 1, n):
        yield from db.execute(f'SELECT {cols} FROM {table} WHERE rowid >= ? AND rowid < ?', (lo, lo + n)).fetchall()
        time.sleep(0.05)


def targets(first):
    db = sqlite3.connect(f'file:{OUT / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    done = {w for w, s in chunks(db, 'works', 'id, status') if s in ('downloaded', 'fulltext_xml')}
    handles, known = {}, {}
    for w, u, land in chunks(db, 'candidates', 'work_id, url, landing_url'):
        if w in done:
            continue
        known.setdefault(w, set()).add(u)
        for x in (u, land or ''):
            m = HANDLE.match(x)
            if m:
                handles.setdefault(w, set()).add(m.group(1))
    order = {w: i for i, w in enumerate(first)}
    return dict(sorted(handles.items(), key=lambda kv: order.get(kv[0], len(order)))), known


def load_cache():
    cache = {}
    if CACHE.exists():
        for line in CACHE.open():
            r = json.loads(line); cache[r['handle']] = r
    return cache


class Paced:
    def __init__(self):
        import requests
        self.s = requests.Session(); self.s.headers['User-Agent'] = UA; self.last = 0.0

    def get(self, url, **kw):
        for attempt in range(4):
            time.sleep(max(0, 3 - (time.monotonic() - self.last))); self.last = time.monotonic()
            try:
                r = self.s.get(url, timeout=(15, 90), **kw)
            except Exception:
                time.sleep(30); continue
            if r.status_code in (429, 503) or (r.status_code == 202 and not r.content):
                print(json.dumps(dict(status=r.status_code, pause_s=600, url=url[-80:])), flush=True)
                time.sleep(600); continue
            return r
        return None


def resolve(handles, known, batch=None):
    cache = load_cache()
    todo = list(dict.fromkeys(h for hs in handles.values() for h in sorted(hs) if h not in cache or cache[h].get('error')))
    print(json.dumps(dict(handles=len({h for hs in handles.values() for h in hs}), to_resolve=len(todo))), flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    web, n = Paced(), Counter()
    with CACHE.open('a') as f:
        for k, h in enumerate(todo):
            r = web.get(f'{API}/pid/find', params={'id': 'hdl:' + h})
            if r is None or r.status_code >= 500:
                rec = dict(error=r.status_code if r is not None else 'failed')
            elif r.status_code != 200:
                rec = dict(files=[], status=r.status_code)
            else:
                item = r.json()
                b = web.get(f'{API}/core/items/{item["uuid"]}/bundles', params={'embed': 'bitstreams', 'size': 50})
                if b is None or b.status_code != 200:
                    rec = dict(item=item['uuid'], error=b.status_code if b is not None else 'failed')
                else:
                    files = []
                    for bd in b.json().get('_embedded', {}).get('bundles', []):
                        if bd.get('name') != 'ORIGINAL':
                            continue
                        for bs in bd.get('_embedded', {}).get('bitstreams', {}).get('_embedded', {}).get('bitstreams', []):
                            files.append(dict(uuid=bs['uuid'], name=bs.get('name'), size=bs.get('sizeBytes')))
                    rec = dict(item=item['uuid'], files=files)
            rec = dict(handle=h, at=datetime.now(timezone.utc).isoformat(), **rec)
            cache[h] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
            n['error' if rec.get('error') else 'pdf' if any((x['name'] or '').lower().endswith('.pdf') for x in rec.get('files', [])) else 'no_pdf'] += 1
            if k % 100 == 99:
                print(json.dumps(dict(resolved=k + 1, of=len(todo), **n)), flush=True)
            if batch and k % batch == batch - 1:
                add(handles, known)
    print(json.dumps(dict(resolved=len(todo), **n)), flush=True)


def add(handles, known):
    cache = load_cache()
    rows, used, n = [], {}, Counter()
    for w, hs in handles.items():
        got = 0
        for h in sorted(hs):
            rec = cache.get(h)
            if not rec or rec.get('error'):
                continue
            used[h] = rec
            for x in rec.get('files', []):
                if not (x['name'] or '').lower().endswith('.pdf') or (x['size'] or 0) > LIMIT:
                    continue
                u = f'{API}/core/bitstreams/{x["uuid"]}/content'
                if u not in known.get(w, ()):
                    rows.append((w, u, f'https://infoscience.epfl.ch/entities/publication/{rec["item"]}')); got += 1
        n['works_gaining' if got else 'works_without_new_pdf'] += 1
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    ev = OUT / 'discovery' / 'claude-epfl-catalog' / 'evidence' / f'infoscience-rest-{stamp}.json'
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text(json.dumps(dict(rule=__doc__, created_at=datetime.now(timezone.utc).isoformat(), records=used)))
    db = sqlite3.connect(str(OUT / 'catalog.sqlite'), timeout=300)
    added = 0
    for attempt in range(20):  # the collector writes to the same catalog: wait out its locks
        try:
            added = sum(db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (w, u, land, None, None, str(ev))).rowcount for w, u, land in rows)
            db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(30)
    for w, u, _ in rows:
        known.setdefault(w, set()).add(u)
    print(json.dumps(dict(candidates_added=added, works=len({r[0] for r in rows}), evidence=str(ev), **n)), flush=True)


def main():
    args = sys.argv[1:]
    first, batch = [], None
    if '--batch' in args:
        i = args.index('--batch'); batch = int(args[i + 1]); del args[i:i + 2]
    if '--first' in args:
        i = args.index('--first'); first = [m['work_id'] for m in json.loads(Path(args[i + 1]).read_text()) if m.get('work_id')]; del args[i:i + 2]
    steps = args or ['resolve', 'add']
    handles, known = targets(first)
    if 'resolve' in steps:
        resolve(handles, known, batch)
    if 'add' in steps:
        add(handles, known)


if __name__ == '__main__':
    main()
