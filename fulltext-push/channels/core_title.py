"""CORE title fallback when the paper's completed DOI query found no links.

Use the existing registered CORE API, pacing, host exclusions and caches. Only
exact long titles with the same first-author family and a stated year within
two years yield candidates. A conflicting returned DOI is rejected. This finds
copy locations; it never supplies paper ownership or download credit.
"""
import contextlib
import fcntl
import json
import time

NAME = 'core_title'


def search(session, query, ctx):
    """One paced API request; errors stop this pass rather than repeat bad batches."""
    time.sleep(2)
    try:
        response = session.get('https://api.core.ac.uk/v3/search/outputs/', params={'q': query, 'limit': 100}, timeout=(15, 120))
    except Exception as exc:
        ctx.n['stopped'] = 'CORE request failed: ' + type(exc).__name__
        return None
    ctx.n[f'core_title_http_{response.status_code}'] += 1
    if response.status_code != 200:
        ctx.n['stopped'] = f'CORE HTTP {response.status_code}; no further requests in this pass'
        return None
    try:
        results = response.json()['results']
        if not isinstance(results, list):
            raise ValueError('CORE results is not a list')
    except (KeyError, ValueError, TypeError):
        ctx.n['stopped'] = 'CORE response format not recognized'
        return None
    remaining = response.headers.get('x-ratelimit-remaining')
    if remaining is not None and remaining.isdigit() and int(remaining) < 5:
        ctx.n['stopped'] = 'CORE rate limit nearly exhausted; no further requests in this pass'
    return results


def APPLIES(school, paper):
    import ftp_common as F
    import bulk_oa as B
    return bool(F.ndoi(paper.r.get('doi')) and len(F.nt(paper.r.get('title'))) >= 30
                and B.fam((paper.r.get('byline') or [''])[0]) and paper.r.get('year'))


def matching_links(record, row):
    import ftp_common as F
    import bulk_oa as B
    import core_search as C
    from channels.core_bulk import _links
    if F.nt(record.get('title')) != F.nt(row.get('title')):
        return []
    first = B.fam(((record.get('authors') or [{}])[0] or {}).get('name') or '')
    if not first or first != B.fam((row.get('byline') or [''])[0]):
        return []
    try:
        if abs(int(record['yearPublished']) - int(row['year'])) > 2:
            return []
    except (KeyError, TypeError, ValueError):
        return []
    doi = F.ndoi(record.get('doi'))
    if doi and doi != F.ndoi(row.get('doi')):
        return []
    return list(dict.fromkeys(u for u in _links(record) if C.usable(u)))


def discover(school, papers, ctx):
    import ftp_common as F
    import bulk_oa as B
    import core_search as C
    from channels.core_bulk import _load
    path = B.DIR / 'core-doi-missing-titles.jsonl'
    done = _load(path)
    doi_done = {}
    if C.CACHE.exists():
        for line in C.CACHE.open():
            try:
                rec = json.loads(line)
                doi_done[rec['doi']] = rec
            except (ValueError, KeyError):
                continue
    def key(p):
        return '|'.join((F.ndoi(p.r['doi']), F.nt(p.r['title']),
                         B.fam((p.r.get('byline') or [''])[0]), str(p.r['year'])))
    chosen = [p for p in papers if F.ndoi(p.r['doi']) in doi_done
              and not doi_done[F.ndoi(p.r['doi'])].get('error')
              and not doi_done[F.ndoi(p.r['doi'])].get('links')]
    todo = list({key(p): p for p in chosen if key(p) not in done or done[key(p)].get('error')}.values())
    ctx.n['core_title_completed_empty_doi_queries'] = len(chosen)
    ctx.n['core_title_to_ask'] = len(todo)
    if todo and not ctx.dry:
        with contextlib.ExitStack() as stack:
            busy = False
            for slot in ('core', 'core_bulk'):
                lock = stack.enter_context((F.P.FT_LOGS / f'run_steps-{slot}.lock').open('a'))
                deadline = time.monotonic() + 120
                while True:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            busy = True
                            break
                        time.sleep(2)
                if busy:
                    break
            if busy:
                ctx.n['stopped'] = 'CORE shared API slot busy'
            else:
                session = ctx.session()
                token = ctx.env('CORE_API_KEY')
                if not token:
                    ctx.n['stopped'] = 'CORE API key unavailable'
                else:
                    session.headers['Authorization'] = 'Bearer ' + token
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('a') as output:
                        # The live API returned500 for a compound title query;
                        # its individual title requests succeeded in the pilot.
                        for start in range(len(todo)):
                            batch = todo[start:start + 1]
                            query = ' OR '.join('title:"%s"' % p.r['title'].replace('"', ' ').replace('\\', ' ')[:250] for p in batch)
                            results = search(session, query, ctx)
                            for p in batch:
                                links = [u for record in results or [] for u in matching_links(record, p.r)]
                                rec = dict(k=key(p), at=F.now(), links=list(dict.fromkeys(links))) if results is not None else dict(k=key(p), at=F.now(), error=True)
                                done[key(p)] = rec
                                output.write(json.dumps(rec) + '\n')
                            output.flush()
                            if ctx.n.get('stopped'):
                                break
    for p in papers:
        rec = done.get(key(p)) if p in chosen else None
        urls = [dict(work_id=p.work_id, url=u, landing_url=u, version=None, source=NAME,
                     detail=json.dumps(dict(matched_by='exact_title_first_author_year', doi_query_empty=True))) for u in (rec or {}).get('links', [])]
        status = 'found' if urls else 'error' if ((rec or {}).get('error') or ctx.n.get('stopped')) else 'none'
        yield ctx.result(p, status, urls, query=f"CORE exact title fallback: {p.r['title']}"[:300])
