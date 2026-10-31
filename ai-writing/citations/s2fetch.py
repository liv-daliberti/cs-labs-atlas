"""Semantic Scholar reference lists, a second, independent source for the citing side (a coverage check on OpenAlex).

OpenAlex holds references mostly where the publisher deposited them with Crossref, so arXiv-only lab papers (and most
2025-2026 papers) have none there. S2 parses references from the PDFs too. For every paragraph-scored lab paper with a
DOI (arXiv DOIs 10.48550/arXiv.X are looked up as ARXIV:X) this fetches, 100 papers per POST /graph/v1/paper/batch:
the paper's externalIds and year, and per reference its paperId, externalIds, year, venue, publicationVenue,
citationCount, publicationTypes and s2FieldsOfStudy.

-> /n/fs/resemble/homogenizing-science/cache/citations/s2.sqlite  table refs(key, query, status, data zlib-json)
The key is read from ~/.config/cs-atlas/s2.env and never printed. One request at a time, >= 1.1 s apart; 429 backs off.
usage: s2fetch.py run | status
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, os, sqlite3, sys, time, zlib
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
DB = P.CACHE / 'citations/s2.sqlite'
FIELDS = ('externalIds,year,referenceCount,references.paperId,references.externalIds,references.year,references.venue,'
          'references.publicationVenue,references.citationCount,references.publicationTypes,references.s2FieldsOfStudy')


def key():
    for line in open(os.path.expanduser('~/.config/cs-atlas/s2.env')):
        if line.startswith('S2_API_KEY='):
            return line.strip().split('=', 1)[1].strip('"\'')
    raise SystemExit('no S2_API_KEY')


def log(**kw):
    print(json.dumps(kw), flush=True)


def targets():
    keys = {json.loads(l)['key'] for l in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt')}
    out = []
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        d = (p.get('doi') or '').lower().replace('https://doi.org/', '').strip()
        if p['key'] not in keys or not d:
            continue
        q = 'ARXIV:' + d.split('arxiv.', 1)[1] if d.startswith('10.48550/arxiv.') else 'DOI:' + d
        out.append((p['key'], q))
    return out


def run():
    c = sqlite3.connect(DB, timeout=600)
    c.execute('create table if not exists refs (key text primary key, query text, status int, data blob, at real)')
    have = {k for k, in c.execute('select key from refs')}
    todo = [t for t in targets() if t[0] not in have]
    log(todo=len(todo))
    s, k, last = requests.Session(), key(), 0.0
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        for attempt in range(12):
            time.sleep(max(0.0, 1.1 - (time.time() - last))); last = time.time()
            try:
                r = s.post('https://api.semanticscholar.org/graph/v1/paper/batch', params={'fields': FIELDS},
                           json={'ids': [q for _, q in chunk]}, headers={'x-api-key': k}, timeout=300)
            except requests.RequestException as e:
                log(error=type(e).__name__); time.sleep(10); continue
            if r.status_code == 200:
                break
            time.sleep(min(120, 3 * (attempt + 1)))
        else:
            log(failed_at=i); return
        rows = [(kk, q, int(p is not None), zlib.compress(json.dumps(p).encode()) if p else None, time.time()) for (kk, q), p in zip(chunk, r.json())]
        c.executemany('insert or replace into refs values (?,?,?,?,?)', rows); c.commit()
        if (i // 100) % 25 == 0:
            log(done=i + len(chunk), of=len(todo))
    log(done=len(todo))


def status():
    c = sqlite3.connect(DB)
    log(rows=c.execute('select status, count(*) from refs group by status').fetchall())


if __name__ == '__main__':
    {'run': run, 'status': status}[sys.argv[1]]()
