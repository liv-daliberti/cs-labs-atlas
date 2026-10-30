# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-mit-20261020/tools/mit_dspace_rest.py (sha256 7bcb600b017855354a087b38b0e02a5c65f6e5782525371b7c18d8d743f80466); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""DSpace@MIT files through its machine interfaces, for MIT catalog works without a local copy.

DSpace@MIT (DSpace 7 behind CloudFront) has two front doors. The web front end (an Express server: /handle/...,
/items/..., /bitstreams/<uuid>/download, and hdl.handle.net/1721.1/... which redirects there) rate-limits per client
(x-ratelimit-limit 500; /bitstreams/<uuid>/download answered HTTP 429 with Retry-After 900 on 2026-10-21), so every
collector pass since 2026-10-20 paused dspace.mit.edu after its first request and 1,800 MIT candidates never ran. The
machine interfaces, which robots.txt leaves open (it disallows /server/opensearch only), serve the same files:

  resolve  OAI-PMH GetRecord, metadataPrefix=ore, identifier oai:dspace.mit.edu:1721.1/<n> (one request per handle,
           one request per 8 s, Retry-After honoured on 429/503) lists the item's ORIGINAL files as ORE 'aggregates'
           links with title, type and length. Cached in raw/dspace_ore.jsonl (resumable; failures asked again).
  add      every aggregated PDF (<= 500 MiB) of a handle the work already cites (a candidate or landing URL on
           hdl.handle.net/1721.1/, dspace.mit.edu/handle/1721.1/ or dspace.mit.edu/bitstream/[handle/]1721.1/) becomes
           the candidate https://dspace.mit.edu/server/api/core/bitstreams/<uuid>/content (REST; it redirects to the
           repository's signed file store cf003.cdn.4science.cloud, approved in tools/mit_collector_wrapper.py).
           No new work-to-item association is made: the handle comes from the work's own candidates, and the
           collector's identity check (title in the PDF) still applies.
Evidence -> data/fulltext/mit/discovery/claude-mit-catalog/evidence/dspace-ore-<stamp>.json.
usage: mit_dspace_rest.py [resolve] [add] [--first <missing_mit.json>] [--batch N]
       (default: both; --first asks those works first; --batch adds candidates after every N resolved handles)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-mit-20261020'  # vendored: the data root (was Path(__file__).resolve().parents[1])
OUT = P.STORES / 'mit'
CACHE = STAGE / 'raw' / 'dspace_ore.jsonl'
OAI = 'https://dspace.mit.edu/server/oai/request'
REST = 'https://dspace.mit.edu/server/api/core/bitstreams/{}/content'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
HANDLE = re.compile(r'^https?://(?:hdl\.handle\.net|dspace\.mit\.edu/handle|dspace\.mit\.edu/bitstream(?:/handle)?)/1721\.1/(\d+)(?:[/?#]|$)')
LINK = re.compile(r'<atom:link rel="http://www\.openarchives\.org/ore/terms/aggregates" href="https://dspace\.mit\.edu/bitstreams/'
                  r'([0-9a-f-]{36})/download"([^>]*)/>')
LIMIT = 500 * 1024 * 1024


def chunks(db, sql_from, cols, n=20000):
    hi = db.execute(f'SELECT MAX(rowid) FROM {sql_from}').fetchone()[0] or 0
    for lo in range(0, hi + 1, n):
        yield from db.execute(f'SELECT {cols} FROM {sql_from} WHERE rowid >= ? AND rowid < ?', (lo, lo + n)).fetchall()
        time.sleep(0.05)


def targets(first):
    """{work id: set of handle numbers} for works without a copy, and the URLs each work already has."""
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


def resolve(handles, known, batch=None):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    cache = load_cache()
    todo = list(dict.fromkeys(h for hs in handles.values() for h in sorted(hs) if h not in cache or cache[h].get('error')))
    print(json.dumps(dict(handles=len({h for hs in handles.values() for h in hs}), to_resolve=len(todo))), flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    last, n = 0.0, Counter()
    with CACHE.open('a') as f:
        for k, h in enumerate(todo):
            rec = None
            for attempt in range(5):
                time.sleep(max(0, 8 - (time.monotonic() - last))); last = time.monotonic()
                try:
                    r = s.get(OAI, params={'verb': 'GetRecord', 'metadataPrefix': 'ore', 'identifier': f'oai:dspace.mit.edu:1721.1/{h}'}, timeout=(15, 90))
                except Exception as e:
                    rec = dict(error=str(e)[:120]); time.sleep(30); continue
                if r.status_code in (429, 503):
                    wait = int(r.headers.get('Retry-After') or 120)
                    print(json.dumps(dict(status=r.status_code, retry_after=wait, at=k)), flush=True)
                    rec = dict(error=r.status_code); time.sleep(min(wait, 1800)); continue
                if r.status_code != 200:
                    rec = dict(error=r.status_code); break
                if 'idDoesNotExist' in r.text:
                    rec = dict(files=[], oai='idDoesNotExist'); break
                files = []
                for uuid, attrs in LINK.findall(r.text):
                    a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
                    files.append(dict(uuid=uuid, title=a.get('title'), type=a.get('type'), length=int(a['length']) if a.get('length', '').isdigit() else None))
                rec = dict(files=files); break
            rec = dict(handle=h, at=datetime.now(timezone.utc).isoformat(), **rec)
            cache[h] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
            n['error' if rec.get('error') else 'pdf' if any(x['type'] == 'application/pdf' for x in rec.get('files', [])) else 'no_pdf'] += 1
            if k % 100 == 99:
                print(json.dumps(dict(resolved=k + 1, of=len(todo), **n)), flush=True)
            if batch and k % batch == batch - 1:
                f.flush(); add(handles, known)
    print(json.dumps(dict(resolved=len(todo), **n)), flush=True)


def add(handles, known):
    cache = load_cache()
    rows, used, n = [], {}, Counter()
    for w, hs in handles.items():
        got = 0
        for h in sorted(hs):
            rec = cache.get(h)
            if not rec or rec.get('error'):
                n['unresolved_handle'] += 1; continue
            used[h] = rec
            for x in rec['files']:
                if x['type'] != 'application/pdf' or (x['length'] or 0) > LIMIT:
                    continue
                u = REST.format(x['uuid'])
                if u not in known.get(w, ()):
                    rows.append((w, u, f'https://hdl.handle.net/1721.1/{h}')); got += 1
        n['works_gaining' if got else 'works_without_new_pdf'] += 1
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    ev = OUT / 'discovery' / 'claude-mit-catalog' / 'evidence' / f'dspace-ore-{stamp}.json'
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
