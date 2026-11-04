"""Channel core_bulk (2026-11-04, owner: bulk open-access sources, 3): CORE records matched LOCALLY to our lab papers, DOI first, then
normalized title plus first author. The repository download links of a matching record (sourceFulltextUrls, and downloadUrl when it is
not core.ac.uk) are candidates on the hosts the collectors may use (core_search.usable).

Terms (read 2026-11-04, docs/CHANNELS.md): the CORE bulk DATASET is ODC-BY but its download is for users representing registered
organisations (individuals are sent to the API): we have no registration, so the dataset is not used. The CORE API v3 is used with the owner's
registered key, as the `core` channel always has (docs: free for individuals and public research organisations for unfunded research;
the owner confirms that this is such use); search queries at the documented rate (the x-ratelimit headers are honoured, 2 s between requests), repository
links only, no reader (core.ac.uk) copies. core.ac.uk's robots.txt disallows only /search (the website, not api.core.ac.uk).

  DOI      the lab paper's DOI -> doi:"..." queries, 25 per request, through the `core` step's own cache (core_search.CACHE), so no DOI is asked twice
  title    papers without a DOI (title >= 20 normalized characters): title:"..." queries, 8 per request; a result counts only when its normalized
           title equals the paper's, the first author's family name equals the result's first author, and the year is within 2
           (cache FT_RAW/bulk-oa/core-titles.jsonl, one record per paper title key)
"""
import json
import os
import time
from collections import defaultdict

NAME = 'core_bulk'


def APPLIES(school, paper):
    import ftp_common as F
    d = F.ndoi(paper.r.get('doi'))
    if d:
        return not d.startswith('10.48550/') and '"' not in d and '\\' not in d
    return len(F.nt(paper.r.get('title'))) >= 20


def _search(s, q, limit):
    """-> list of outputs, or None after repeated failures; waits out the rate-limit window when it runs low."""
    for _attempt in range(4):
        time.sleep(2)
        try:
            r = s.get('https://api.core.ac.uk/v3/search/outputs/', params={'q': q, 'limit': limit}, timeout=(15, 200))
        except Exception:
            time.sleep(30)
            continue
        left = r.headers.get('x-ratelimit-remaining')
        if r.status_code == 200:
            if left is not None and int(left) < 5:
                time.sleep(60)
            return r.json().get('results') or []
        time.sleep(120 if r.status_code == 429 else 20)
    return None


def _links(o):
    return [u for u in (o.get('sourceFulltextUrls') or []) + [o.get('downloadUrl') or ''] if u]


def _load(path):
    out = {}
    if path.exists():
        for line in path.open():
            try:
                r = json.loads(line)
                out[r['k']] = r
            except (ValueError, KeyError):
                pass
    return out


def discover(school, papers, ctx):
    import requests
    import bulk_oa as B
    import core_search as cs
    import ftp_common as F
    s = requests.Session()
    s.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']
    # ---- DOIs through the shared cache
    done = {}
    if cs.CACHE.exists():
        for line in cs.CACHE.open():
            try:
                r = json.loads(line)
                done[r['doi']] = r
            except ValueError:
                pass
    dois = [F.ndoi(p.r['doi']) for p in papers if p.r.get('doi')]
    todo = list(dict.fromkeys(d for d in dois if d not in done or done[d].get('error')))
    ctx.n['core_bulk_dois'], ctx.n['core_bulk_dois_asked'] = len(set(dois)), len(todo)
    if todo and not ctx.dry:
        with cs.CACHE.open('a') as f:
            for i in range(0, len(todo), 25):
                chunk = todo[i:i + 25]
                res = _search(s, ' OR '.join(f'doi:"{d}"' for d in chunk), 100)
                got = defaultdict(list)
                for o in res or []:
                    d = (o.get('doi') or '').lower()
                    if d in chunk:
                        got[d] += _links(o)
                at = F.now()
                for d in chunk:
                    rec = dict(doi=d, at=at, links=list(dict.fromkeys(got.get(d, [])))) if res is not None else dict(doi=d, at=at, error=True)
                    done[d] = rec
                    f.write(json.dumps(rec) + '\n')
                f.flush()
    # ---- titles of the papers without a DOI
    tpath = B.DIR / 'core-titles.jsonl'
    tdone = _load(tpath)
    nodoi = [p for p in papers if not p.r.get('doi')]
    keys = {}
    for p in nodoi:
        fam0 = B.fam((p.r.get('byline') or [''])[0])
        keys[p.work_id] = f"{F.nt(p.r.get('title'))}|{fam0}"
    ttodo = [p for p in nodoi if keys[p.work_id] not in tdone or tdone[keys[p.work_id]].get('error')]
    ctx.n['core_bulk_titles'], ctx.n['core_bulk_titles_asked'] = len(nodoi), len(ttodo)
    if ttodo and not ctx.dry:
        B.DIR.mkdir(parents=True, exist_ok=True)
        with tpath.open('a') as f:
            for i in range(0, len(ttodo), 8):
                chunk = ttodo[i:i + 8]
                q = ' OR '.join('title:"%s"' % p.r['title'].replace('"', ' ').replace('\\', ' ')[:250] for p in chunk)
                res = _search(s, q, 100)
                at = F.now()
                for p in chunk:
                    k = keys[p.work_id]
                    if res is None:
                        rec = dict(k=k, at=at, error=True)
                    else:
                        links = []
                        for o in res:
                            if F.nt(o.get('title')) != F.nt(p.r['title']):
                                continue
                            au = [B.fam((a or {}).get('name') or '') for a in o.get('authors') or []]
                            y, y0 = o.get('yearPublished'), p.r.get('year')
                            if (au[:1] or [''])[0] != B.fam((p.r.get('byline') or [''])[0]):
                                continue
                            if y and y0 and abs(int(y) - int(y0)) > 2:
                                continue
                            links += _links(o)
                        rec = dict(k=k, at=at, links=list(dict.fromkeys(links)))
                    tdone[k] = rec
                    f.write(json.dumps(rec) + '\n')
                f.flush()
    for p in papers:
        if p.r.get('doi'):
            links, how = (done.get(F.ndoi(p.r['doi'])) or {}).get('links') or [], 'doi'
        else:
            links, how = (tdone.get(keys.get(p.work_id)) or {}).get('links') or [], 'title_author'
        rows = [dict(work_id=p.work_id, url=u, landing_url=u, version=None, source='core_bulk', detail=json.dumps(dict(matched_by=how)))
                for u in links if cs.usable(u)]
        yield ctx.result(p, 'found' if rows else 'none', rows, query=f"CORE search/outputs by {how}: {p.r.get('doi') or p.r.get('title')}"[:300])
