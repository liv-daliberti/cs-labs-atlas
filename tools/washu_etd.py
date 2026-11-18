"""WashU Scholarly Repository ETD records (bepress Digital Commons) as a student source: dissertations whose record page names a Committee Chair.

crawl   fetch the record pages of one ETD collection (default eng_etds, from its sitemap), newest ids first, at least DELAY seconds apart
        (robots.txt of repository.library.washu.edu: '*' group only, no AI-agent rule, no Crawl-delay; /cgi/ and /do/ are never touched).
        Pages land in the school's capture container (live table), so a rerun reuses them.
parse   read the stored record pages into <out>.json: author, title, year, degree, department, Committee Chair, Committee Members,
        url, sha256 of the stored bytes, and a verbatim quote of the page text.
usage: washu_etd.py crawl|parse|count [--coll eng_etds[,chemeng_etds,...]] [--delay 5] [--limit N] [--out PATH] [--db FILE]
count   the record ids of each collection's sitemap (one request each), stored records among them
--db    a separate capture container (a deep-dive crawl running beside other jobs writes its own sqlite; parse reads the same file)
"""
import argparse
import html
import importlib.util
import json
import re
import time
from pathlib import Path

# Load the trusted sibling explicitly; preserve python -I for fetched input handling.
_spec = importlib.util.spec_from_file_location('school_web', Path(__file__).resolve().with_name('school_web.py'))
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

KEY = 'washu'
BASE = 'https://repository.library.washu.edu'


def record_urls(c, coll):
    r = W.live(c, f'{BASE}/{coll}/sitemap.xml')
    if r is None or r[0] != 200:
        raise SystemExit(f'sitemap not readable: {r and r[0]}')
    raw = W.live_html(c, f'{BASE}/{coll}/sitemap.xml')
    urls = re.findall(r'<loc>([^<]+)</loc>', raw)
    recs = [u for u in urls if re.search(rf'/{coll}/\d+/?$', u)]
    return sorted(recs, key=lambda u: -int(re.search(r'/(\d+)/?$', u).group(1)))


def use_db(path):
    if path:
        W.db_path = lambda key, _p=Path(path): _p


def count(colls):
    c = W.con(KEY)
    for coll in colls:
        urls = record_urls(c, coll)
        have = sum(1 for u in urls if c.execute('select 1 from live where url=?', (u,)).fetchone())
        print(json.dumps(dict(coll=coll, records=len(urls), stored=have)), flush=True)
        time.sleep(3)


def crawl(coll, delay, limit):
    c = W.con(KEY)
    urls = record_urls(c, coll)
    print(len(urls), 'records in', coll, flush=True)
    n = 0
    for u in urls:
        if c.execute('select 1 from live where url=?', (u,)).fetchone():
            continue
        t0 = time.time()
        res = W.live(c, u)
        n += 1
        st = res[0] if res else None
        if st != 200:
            print('stop: status', st, u, flush=True)
            if st in (403, 429, 503, 999, None):
                return
        if n % 50 == 0:
            print(n, u, flush=True)
        if limit and n >= limit:
            return
        time.sleep(max(0.0, delay - (time.time() - t0)))


def field(t, fid):
    m = re.search(rf"<div id='{fid}' class='element'>\s*<h2 class='field-heading'>[^<]*</h2>\s*<p>(.*?)</p>", t, re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip() if m else ''


def meta(t, name):
    m = re.search(rf'<meta name="{name}" content="([^"]*)"', t)
    return html.unescape(m.group(1)).strip() if m else ''


def split_names(s):
    return [x.strip() for x in re.split(r'\s*[;,]\s*|\s+and\s+', s) if x.strip()]


def parse(colls, out):
    c = W.con(KEY)
    rows = []
    for coll in colls:
        rows.extend(parse_one(c, coll))
    Path(out).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(len(rows), 'dissertation records with a Committee Chair ->', out)


def parse_one(c, coll):
    rows = []
    for u, sha in c.execute("select url, sha256 from live where url like ? and status=200", (f'{BASE}/{coll}/%',)):
        if not re.search(rf'/{coll}/\d+/?$', u):
            continue
        t = W.live_html(c, u)
        if 'bepress_citation_dissertation' not in t:
            continue
        chair = field(t, 'advisor1')
        if not chair:
            continue
        flat = W.flat(W.live(c, u)[2])
        author = meta(t, 'bepress_citation_author')
        i = flat.find('Committee Chair')
        quote = flat[i:i + len('Committee Chair') + 1 + len(chair)] if i >= 0 else ''
        rows.append({
            'collection': coll, 'url': u, 'sha256': sha, 'author': author, 'title': meta(t, 'bepress_citation_title'),
            'year': meta(t, 'bepress_citation_date')[:4], 'degree': meta(t, 'bepress_citation_dissertation_name'),
            'department': field(t, 'department'), 'chair': chair, 'chairs': split_names(chair),
            'members': field(t, 'advisor2'), 'quote': quote, 'quote_in_text': quote in flat,
            'author_in_text': author.split(',')[0] in flat,
        })
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['crawl', 'parse', 'count'])
    ap.add_argument('--coll', default='eng_etds')
    ap.add_argument('--db', default='')
    ap.add_argument('--delay', type=float, default=5.0)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default='washu-etd.json')
    a = ap.parse_args()
    use_db(a.db)
    colls = [x for x in a.coll.split(',') if x]
    if a.cmd == 'count':
        count(colls)
    elif a.cmd == 'crawl':
        for coll in colls:
            crawl(coll, a.delay, a.limit)
    else:
        parse(colls, a.out)
