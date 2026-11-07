"""Experiment B step 1: exact pairing of universe papers with arXiv records, then the version listing from arXiv's public cloud mirror.

  rv_match.py match                 universe papers -> arXiv id (DOI field, 10.48550 DOI, exact normalized title with a unique record and a year window)
  rv_match.py versions [-j N]       the bucket's object listing per matched id (resumable cache in DATA/revision.sqlite `versions`): which vN exist
Never arxiv.org; the bucket is storage.googleapis.com (docs/CHANNELS.md arxiv_bulk).
Table matches(paper_id PK, arxiv_id, how, arxiv_title, created, oai_doi); versions(arxiv_id PK, n_versions, listed_at).
"""
import argparse
import gzip
import json  # noqa: F401
import re
import sqlite3
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import rv_common as C


def nt(t):
    t = re.sub(r'<[^>]+>', ' ', t or '')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def connect():
    C.DATA.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(C.DB, timeout=600)
    db.execute('create table if not exists matches (paper_id text primary key, arxiv_id text, how text, arxiv_title text, created text, oai_doi text)')
    db.execute('create table if not exists versions (arxiv_id text primary key, n_versions int, listed_at text)')
    return db


def oai_index():
    by_doi, by_t, by_id = {}, defaultdict(list), {}
    n = 0
    for f in sorted(C.OAI_DIR.glob('*.jsonl.gz')):
        for line in gzip.decompress(f.read_bytes()).decode().splitlines():
            if not line:
                continue
            r = json.loads(line)
            n += 1
            rec = (re.sub(r'v\d+$', '', r['id']), r['title'], r.get('created') or '', r.get('doi') or '')
            by_id[rec[0]] = rec
            for d in (r.get('doi') or '').lower().split():
                by_doi.setdefault(ndoi(d), rec)
            k = nt(r['title'])
            if len(k) >= 20:
                by_t[k].append(rec)
    return by_doi, by_t, by_id, n


def title_compatible(a, b):
    x, y = nt(a), nt(b)
    return bool(x and y and (x == y or x.startswith(y) or y.startswith(x)))


def cmd_match():
    import pandas as pd
    by_doi, by_t, by_id, n = oai_index()
    u = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, doi, title, year from papers', u)
    rows, how_n = [], defaultdict(int)
    for r in papers.itertuples():
        d = ndoi(r.doi)
        rec, how = None, None
        if d in by_doi and title_compatible(r.title, by_doi[d][1]):
            rec, how = by_doi[d], 'doi'
        elif d.startswith('10.48550/arxiv.'):
            a = re.sub(r'v\d+$', '', d.split('arxiv.', 1)[1])
            rec = by_id.get(a) or (a, None, '', '')
            how = 'arxiv_doi'
        else:
            hits = [h for h in by_t.get(nt(r.title), []) if r.year and h[2] and -1 <= int(r.year) - int(h[2][:4]) <= 3]
            if len({h[0] for h in hits}) == 1:
                rec, how = hits[0], 'title'
        if rec:
            rows.append((r.paper_id, rec[0], how, rec[1], rec[2], rec[3])); how_n[how] += 1
    db = connect()
    db.execute('delete from matches')
    db.executemany('insert into matches values (?,?,?,?,?,?)', rows); db.commit()
    C.log(oai_records=n, papers=len(papers), matched=len(rows), by=dict(how_n))


def list_one(s, i):
    """[(version, time_created)] of the bucket's objects for one arXiv id (time_created is an upper bound of the version's date); None on failure."""
    tail = i.split('/')[-1]
    yymm = tail.split('.')[0] if '.' in tail else tail[:4]
    prefix = f'arxiv/arxiv/pdf/{yymm}/{tail}v'
    for attempt in range(4):
        try:
            r = s.get(C.API, params={'prefix': prefix, 'fields': 'items(name,timeCreated)'}, timeout=60)
            if r.status_code == 200:
                out = []
                for x in r.json().get('items') or []:
                    m = re.search(re.escape(tail) + r'v(\d+)\.pdf$', x['name'])
                    if m:
                        out.append((int(m.group(1)), x.get('timeCreated')))
                return out
            if r.status_code in (429, 500, 502, 503):
                time.sleep(30 * (attempt + 1)); continue
            return None
        except Exception:
            time.sleep(10)
    return None


def cmd_versions(workers):
    import requests
    db = connect()
    db.execute('create table if not exists version_list (arxiv_id text, v int, time_created text, primary key (arxiv_id, v))')
    have = {a for (a,) in db.execute('select arxiv_id from versions')}
    todo = [a for (a,) in db.execute('select distinct arxiv_id from matches order by arxiv_id') if a not in have]
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    C.log(ids=len(todo) + len(have), to_list=len(todo))
    s = requests.Session(); s.headers['User-Agent'] = C.UA
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for i in range(0, len(todo), 400):
            chunk = todo[i:i + 400]
            res = list(ex.map(lambda a: (a, list_one(s, a)), chunk))
            for a, vs in res:
                if vs is None:
                    continue
                db.executemany('insert or replace into version_list values (?,?,?)', [(a, v, t) for v, t in vs])
                db.execute('insert or replace into versions values (?,?,?)', (a, max([v for v, _ in vs] or [0]), now))
            db.commit()
            done += len(chunk)
            C.log(listed=done, of=len(todo))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['match', 'versions'])
    ap.add_argument('-j', type=int, default=4)
    a = ap.parse_args()
    cmd_match() if a.cmd == 'match' else cmd_versions(a.j)
