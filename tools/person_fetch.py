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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('school')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--deadline', type=int, default=3000, help='seconds; remaining URLs stay queued')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    os.environ['CS_ATLAS_LABPAGE_LIVE_ONLY'] = '1'
    import labpage_audit as L
    DIR.mkdir(parents=True, exist_ok=True)
    store = DIR / f'captures-{a.school}.sqlite'
    kit = L.Kit(a.school)
    os.environ['LPCAP_LOCAL'] = str(store)   # new captures go to the scratch store; reads still cover the school's earlier stores
    kit.store = store
    kit.lpcap.connect(a.school).close()
    out = DIR / f'fetched-{a.school}.jsonl'
    done = {json.loads(line)['url'] for line in out.open()} if out.exists() else set()
    rows = [json.loads(line) for line in (DIR / f'queue-{a.school}.jsonl').open()]
    todo, seen = [], set(done)
    for r in rows:
        u = r.get('url')
        if not u or u in seen or r.get('mode') == 'wayback_only' or SKIP.search(urlsplit(u).hostname or ''):
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
            g = kit.lpcap.fetch(a.school, r['url'])
            body = g.get('content') or b''
            ok = g.get('status') == 200 and bool(body)
            who = r['person']
            named, quote = names_person(body, who) if ok else (False, None)
            res.append(dict(url=r['url'], person=who, role=r.get('role'), kind=r.get('kind'), lab=r.get('lab'), at=at,
                            status=g.get('http_status') or g.get('status'), error=g.get('error'), sha256=g.get('sha256') if ok else None,
                            final_url=g.get('final_url'), names_person=named, quote=quote))
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
