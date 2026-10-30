"""OpenAlex refresh steps (2026-10-29), with the user's key from ~/.config/cs-atlas (ftp_common.load_env; never printed).
OpenAlex charges a daily budget (10,000 credits for this key; a list request costs 1, a title search 10): every request
stops once X-RateLimit-Remaining falls under RESERVE, and every request is logged to raw/openalex_budget.jsonl.

oa_refresh   the missing lab papers' OpenAlex records re-read 50 ids per request (filter=openalex_id:W..|W..), to pick up
             locations added since our cached copy (raw/oa_refresh.jsonl; one refresh per id per 7 days); the fresh
             record's locations -> candidates exactly as the openalex step (ftp_common.oa_location_rows: open pdf_urls and
             repository files / landing pages on usable hosts; PMC -> NLM's S3 copy) plus its arXiv id -> the bulk copy;
             also the paper's own arXiv edition DOIs (10.48550, the hierarchy's 'editions') -> the bulk copy
oa_editions  separate open editions found by title: 15 titles per request (filter=title.search:t1|t2..,is_oa:true,
             per_page=200; commas, pipes and colons removed from the titles); a result is an edition of the paper when it
             is a different OpenAlex work with the same normalized title (>= 20 characters), a year within 2, and an author
             family name shared with the paper's byline -> its arXiv id (bulk copy) or its locations (as above)
             (cache raw/oa_editions.jsonl, one row per query, so a later day continues where the budget stopped)
"""
import json, os, re, time, unicodedata
from collections import defaultdict

import ftp_common as F

RESERVE = 800
BUDGET_LOG = F.HERE / 'raw' / 'openalex_budget.jsonl'
REFRESH = F.HERE / 'raw' / 'oa_refresh.jsonl'
EDITIONS = F.HERE / 'raw' / 'oa_editions.jsonl'
SEL = 'id,doi,title,publication_year,ids,locations,primary_location,best_oa_location,authorships'


class Spent(Exception):
    pass


def get(s, params, kind, n):
    F.load_env()
    p = dict(params, api_key=os.environ.get('OPENALEX_API_KEY', ''))
    for attempt in range(4):
        time.sleep(0.2)
        try:
            r = s.get('https://api.openalex.org/works', params=p, timeout=(15, 120))
        except Exception:
            time.sleep(30); continue
        left = r.headers.get('X-RateLimit-Remaining')
        with BUDGET_LOG.open('a') as f:
            f.write(json.dumps(dict(at=F.now(), kind=kind, status=r.status_code, credits=r.headers.get('X-RateLimit-Credits-Used'), remaining=left)) + '\n')
        n['openalex_requests'] += 1
        n['openalex_credits'] += int(r.headers.get('X-RateLimit-Credits-Used') or 0)
        if r.status_code == 429 or (left is not None and int(left) < RESERVE):
            n['openalex_budget_stop'] = 1
            raise Spent(left)
        if r.status_code == 200:
            return r.json().get('results') or []
        time.sleep(20)
    return None


def fam(name):
    toks = [re.sub(r'[^a-z]', '', t) for t in unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower().split()]
    toks = [t for t in toks if t and t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return toks[-1] if toks and len(toks[-1]) >= 3 else ''


def rows_from(w, body, known, has_arxiv, arx, pmc, src):
    rows, p = F.oa_location_rows(w, body)
    for r in rows:
        r['source'] = src
    if p and not any('pmc-oa-opendata' in u for u in known[w]):
        pmc.setdefault(w, set()).update(p)
    a = F.arxiv_of({}, body)
    if a and not has_arxiv(known[w]) and w not in arx:
        arx[w] = a
    return rows


def finish(rows, arx, pmc, n, src):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    memo = {}
    for w, p in pmc.items():
        rows += [dict(r, source=src + '_pmc') for r in F.pmc_rows(w, p, memo, s)]
    brows, n[src + '_arxiv_not_in_bulk'] = F.bulk_rows(arx, src + '_arxiv_bulk')
    n[src + '_arxiv_bulk'] = len(brows)
    return rows + brows


def step_oa_refresh(school, miss, known, n, has_arxiv):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    cache = {}
    if REFRESH.exists():
        for line in REFRESH.open():
            try:
                x = json.loads(line); cache[x['id']] = x
            except ValueError:
                pass
    week = time.time() - 7 * 86400
    fresh = lambda x: x and time.mktime(time.strptime(x['at'][:19], '%Y-%m-%dT%H:%M:%S')) > week
    todo = list(dict.fromkeys(r['oa'] for r, _ in miss if r.get('oa') and not fresh(cache.get(r['oa']))))
    n['oa_refresh_to_ask'] = len(todo)
    try:
        with REFRESH.open('a') as f:
            for i in range(0, len(todo), 50):
                part = todo[i:i + 50]
                res = get(s, dict(filter='openalex_id:' + '|'.join(F.oa_short(x) for x in part), select=SEL, per_page=50), 'oa_refresh', n)
                if res is None:
                    continue
                for b in res:
                    x = dict(id=b['id'], at=F.now(), body=b); cache[b['id']] = x
                    f.write(json.dumps(x) + '\n')
                for x in part:
                    if x not in {b['id'] for b in res}:
                        n['oa_refresh_gone'] += 1
    except Spent:
        pass
    rows, arx, pmc = [], {}, {}
    for r, w in miss:
        x = cache.get(r.get('oa'))
        if x:
            rows += rows_from(w, x['body'], known, has_arxiv, arx, pmc, 'openalex_refresh')
        for d in r.get('editions') or []:
            d = F.ndoi(d.get('doi'))
            if d.startswith('10.48550/arxiv.') and not has_arxiv(known[w]) and w not in arx:
                arx[w] = d.split('arxiv.', 1)[1]; n['oa_refresh_edition_arxiv'] += 1
    return finish(rows, arx, pmc, n, 'openalex_refresh')


def step_oa_editions(school, miss, known, n, has_arxiv):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    cache = {}
    if EDITIONS.exists():
        for line in EDITIONS.open():
            try:
                x = json.loads(line); cache[x['q']] = x['results']
            except ValueError:
                pass
    want = [(r, w) for r, w in miss if len(F.nt(r.get('title'))) >= 20 and not has_arxiv(known[w])]
    clean = lambda t: re.sub(r'\s+', ' ', re.sub(r'[,|:;"]', ' ', re.sub(r'<[^>]+>', ' ', t or ''))).strip()
    titles = sorted({clean(r['title']) for r, _ in want})
    done_titles = {t for q in cache for t in q.split('|')}
    todo = [t for t in titles if t not in done_titles]
    n['oa_editions_titles'] = len(titles); n['oa_editions_to_ask'] = len(todo)
    by_nt = defaultdict(list)
    try:
        with EDITIONS.open('a') as f:
            for i in range(0, len(todo), 15):
                q = '|'.join(todo[i:i + 15])
                res = get(s, dict(filter=f'title.search:{q},is_oa:true', select=SEL, per_page=200), 'oa_editions', n)
                if res is None:
                    continue
                keep = [b for b in res if F.nt(b.get('title')) in {F.nt(t) for t in todo[i:i + 15]}]
                cache[q] = keep
                f.write(json.dumps(dict(q=q, at=F.now(), results=keep)) + '\n')
    except Spent:
        pass
    for res in cache.values():
        for b in res:
            by_nt[F.nt(b.get('title'))].append(b)
    rows, arx, pmc = [], {}, {}
    for r, w in want:
        fams = {fam(x) for x in (r.get('byline') or []) + (r.get('pis') or [])} - {''}
        for b in by_nt.get(F.nt(r['title']), []):
            if b['id'] == r.get('oa') or (r.get('year') and b.get('publication_year') and abs(b['publication_year'] - r['year']) > 2):
                continue
            bf = {fam(a.get('author', {}).get('display_name')) for a in b.get('authorships') or []} - {''}
            if not fams & bf:
                n['oa_editions_no_shared_author'] += 1; continue
            n['oa_editions_matched'] += 1
            rows += rows_from(w, b, known, has_arxiv, arx, pmc, 'openalex_edition')
    return finish(rows, arx, pmc, n, 'openalex_edition')
