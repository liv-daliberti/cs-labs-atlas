"""Live, polite fetch of the person-website queue (scratch/websites-b/queue-<school>.jsonl) with the lab-page audit's fetcher.

Uses labpage_audit.Kit in live-only mode: robots.txt honoured (a host naming ClaudeBot / anthropic-ai / Claude-Web is never used), per-host
pacing and Crawl-delay from the toolkit, a challenged or 403/429 host is remembered and skipped, a charter 'wayback-only' host is not
fetched live, and nothing is fetched from Wayback here. Pages go to the existing capture-store format (lpcap schema), in
<scratch>/websites-b/captures-<school>.sqlite, never as loose files. Results (one line per URL, resumable) go to
<scratch>/websites-b/fetched-<school>.jsonl; person_websites.py reads them.

  person_fetch.py <school> [--workers 8] [--deadline 3000] [--limit N]
"""
import argparse
import concurrent.futures as cf
import datetime
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import atlas_paths as P

DIR = Path(os.environ.get('CS_WEBSITES_DIR') or P.ROOT / 'scratch' / 'websites-b')
SKIP = re.compile(r'(?:^|\.)(?:scholar\.google\.[a-z.]+|linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|researchgate\.net|'
                  r'academia\.edu|orcid\.org|dblp\.org|mathgenealogy\.org|academictree\.org|semanticscholar\.org|github\.com|'
                  r'deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu)$', re.I)
TAGS = re.compile(r'<(script|style)\b.*?</\1>|<[^>]+>', re.S | re.I)


def text_of(body):
    import html
    import unicodedata
    t = html.unescape(TAGS.sub(' ', body.decode('utf-8', 'replace')))
    t = unicodedata.normalize('NFKD', t)
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', ''.join(c for c in t if not unicodedata.combining(c)).lower()).split())


def names_person(body, person):
    """(True, quote) when the page text holds the person's first and last name; the quote is the text around the last name."""
    t = text_of(body)
    toks = [w for w in re.sub(r'[^a-z ]+', ' ', text_of(person.encode())).split() if len(w) > 1]
    if len(toks) < 2:
        return False, None
    if toks[0] in t.split() and toks[-1] in t.split():
        i = t.find(toks[-1])
        return True, t[max(0, i - 60):i + 80]
    return False, None


def plausible_owner(url, person):
    """A name token (3+ letters) of the person appears in the URL's host or path, e.g. eunhyesong.info, /~jag, /faculty/linsey."""
    import unicodedata
    u = unicodedata.normalize('NFKD', url or '').encode('ascii', 'ignore').decode().lower()
    toks = [w for w in re.sub(r'[^a-z ]+', ' ', unicodedata.normalize('NFKD', person).encode('ascii', 'ignore').decode().lower()).split() if len(w) >= 3]
    return any(t in u for t in toks) or any(t[:3] in re.sub(r'[^a-z]', '', urlsplit(u).path) for t in toks[-1:])


GENERIC = re.compile(r'feedback|post-a-job|machineshop|studentaffairs|life-design|/directory|/jobs?\b|careers|/news|/events?\b|/contact|login|/admissions', re.I)


def last_name_on_page(body, person):
    t = text_of(body).split()
    toks = [w for w in re.sub(r'[^a-z ]+', ' ', text_of(person.encode())).split() if len(w) > 1]
    return bool(toks) and toks[-1] in t


def registrable(host):
    parts = (host or '').lower().split('.')
    k = 3 if len(parts) >= 3 and parts[-2] in ('co', 'ac', 'edu', 'com', 'org', 'gov', 'net') else 2
    return '.'.join(parts[-k:])


MAX_HOPS = 5


def follow(kit, school, url, locations):
    """Fetch url; follow same-registrable-domain 301/302/307/308 redirects (max 5 hops). Each hop goes through the toolkit's fetch,
    so robots.txt, AI-agent groups, pacing and host refusals are checked per hop. -> (result, hops [urls visited after the first])."""
    g, hops, cur = kit.lpcap.fetch(school, url), [], url
    while g.get('status') in (301, 302, 303, 307, 308) or g.get('http_status') in (301, 302, 307, 308) and g.get('status') is None:
        loc = locations.get(cur)
        if not loc or len(hops) >= MAX_HOPS:
            g['error'] = g.get('error') or ('redirect-without-location' if not loc else 'too-many-redirects')
            break
        from urllib.parse import urljoin
        dest = urljoin(cur, loc)
        if registrable(urlsplit(dest).hostname) != registrable(urlsplit(url).hostname) or urlsplit(dest).scheme not in ('http', 'https'):
            g['error'] = 'redirect-to-other-site'
            g['redirect_to'] = dest
            break
        hops.append(dest)
        cur = dest
        g = kit.lpcap.fetch(school, dest)
    return g, hops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('school')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--deadline', type=int, default=3000, help='seconds; remaining URLs stay queued')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--refetch-redirects', action='store_true', help='re-fetch URLs whose recorded result was an unfollowed 3xx')
    a = ap.parse_args()
    os.environ['CS_ATLAS_LABPAGE_LIVE_ONLY'] = '1'
    import labpage_audit as L
    DIR.mkdir(parents=True, exist_ok=True)
    store = DIR / f'captures-{a.school}.sqlite'
    kit = L.Kit(a.school)
    os.environ['LPCAP_LOCAL'] = str(store)   # new captures go to the scratch store; reads still cover the school's earlier stores
    kit.store = store
    kit.lpcap.connect(a.school).close()
    locations = {}
    send = kit.lpcap._sess.send

    def send_keep_location(request, **kw):   # the live-only transport returns 3xx unfollowed; remember where it points
        r = send(request, **kw)
        if getattr(r, 'status_code', None) in (301, 302, 303, 307, 308) and r.headers.get('Location'):
            locations[request.url] = r.headers['Location']
        return r
    kit.lpcap._sess.send = send_keep_location
    out = DIR / f'fetched-{a.school}.jsonl'
    latest = {}
    if out.exists():
        for line in out.open():
            x = json.loads(line)
            latest[x['url']] = x
    done = {u for u, x in latest.items() if not (a.refetch_redirects and x.get('status') in (301, 302, 303, 307, 308))}
    rows = [json.loads(line) for line in (DIR / f'queue-{a.school}.jsonl').open()]
    todo, seen = [], set(done)
    for r in rows:
        u = r.get('url')
        if not u or u in seen or r.get('mode') == 'wayback_only' or SKIP.search(urlsplit(u).hostname or ''):
            continue
        if a.refetch_redirects and u not in latest:
            continue
        seen.add(u)
        todo.append(r)
    byhost = {}
    for r in todo[:a.limit]:
        byhost.setdefault(urlsplit(r['url']).hostname or '', []).append(r)
    t0 = datetime.datetime.now()

    def work(group):
        res = []
        for r in group:
            if (datetime.datetime.now() - t0).total_seconds() > a.deadline:
                break
            at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
            g, hops = follow(kit, a.school, r['url'], locations)
            body = g.get('content') or b''
            ok = g.get('status') == 200 and bool(body)
            who = r['person']
            named, quote = names_person(body, who) if ok else (False, None)
            res.append(dict(url=r['url'], person=who, role=r.get('role'), kind=r.get('kind'), lab=r.get('lab'), at=at,
                            status=g.get('http_status') or g.get('status'), error=g.get('error'), sha256=g.get('sha256') if ok else None,
                            final_url=g.get('final_url') or r['url'], redirect_hops=hops or None, redirect_to=g.get('redirect_to'),
                            names_person=named, last_name_on_page=bool(ok and last_name_on_page(body, who)), quote=quote))
        return res

    n = 0
    with cf.ThreadPoolExecutor(a.workers) as ex, out.open('a') as f:
        for res in ex.map(work, byhost.values()):
            for x in res:
                f.write(json.dumps(x, ensure_ascii=False) + '\n')
                n += 1
            f.flush()
    print(a.school, 'queued', len(todo), 'fetched_now', n, 'previously_done', len(done))


if __name__ == '__main__':
    sys.exit(main())
