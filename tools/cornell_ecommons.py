"""Cornell eCommons (DSpace 7) PhD dissertations as a student source (stage 6, source 1 in the preference order): the record's chair
(`dc.contributor.chair`, older records `dc.contributor.advisor`), committee, author, title, year and discipline.

Reads the repository's own REST API (https://ecommons.cornell.edu/server/api/discover/search/objects), never the web front end: robots.txt
(checked 2026-11-24, no AI-agent group, Crawl-delay 2) disallows /search, /browse/*, /entities/*, /server/opensearch and similar but not /server/api.
The OAI-PMH endpoint answers only deleted headers for the thesis collections, so it is not usable for this. Pages go through school_web.live
(robots, per-host delay, stored bytes with sha256 in the school's capture container), so a rerun reuses them.

crawl   fetch every page (size 100) of PhD records issued 2016-2027, DELAY seconds apart
parse   read the stored pages into <out>.json: handle, author, title, year, discipline, degree, chair, committee, url, page url + sha256
usage: cornell_ecommons.py crawl|parse [--delay 2.5] [--limit-pages N] [--out PATH]
"""
import argparse
import json
import sys
import urllib.parse
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402

KEY = 'cornell'
API = 'https://ecommons.cornell.edu/server/api/discover/search/objects'
QUERY = 'thesis.degree.level:"Doctor of Philosophy" AND dc.date.issued:[2016 TO 2027]'


def page_url(n):
    q = dict(query=QUERY, dsoType='ITEM', size=100, page=n, sort='dc.date.issued,asc')
    return API + '?' + urllib.parse.urlencode(q)


def vals(meta, k):
    return [v['value'] for v in meta.get(k) or [] if v.get('value')]


def records(doc, page, sha):
    """Rows of one search-result JSON document."""
    out = []
    for o in doc['_embedded']['searchResult']['_embedded']['objects']:
        it = o['_embedded']['indexableObject']
        m = it.get('metadata') or {}
        chair = vals(m, 'dc.contributor.chair') or vals(m, 'dc.contributor.advisor')
        issued = (vals(m, 'dc.date.issued') or [''])[0]
        out.append(dict(handle=it.get('handle'), url=f"https://hdl.handle.net/{it.get('handle')}", title=it.get('name'),
                        author=(vals(m, 'dc.contributor.author') or [None])[0], year=int(issued[:4]) if issued[:4].isdigit() else None,
                        discipline=(vals(m, 'thesis.degree.discipline') or [None])[0], degree=(vals(m, 'thesis.degree.name') or [None])[0],
                        level=(vals(m, 'thesis.degree.level') or [None])[0], chair=chair, chair_field='dc.contributor.chair' if vals(m, 'dc.contributor.chair') else 'dc.contributor.advisor',
                        committee=vals(m, 'dc.contributor.committeeMember'), page_url=page, page_sha256=sha))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['crawl', 'parse'])
    ap.add_argument('--delay', type=float, default=2.5)
    ap.add_argument('--limit-pages', type=int, default=0)
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    c = W.con(KEY)
    rows, n, total = [], 0, None
    while True:
        url = page_url(n)
        r = W.live(c, url, min_delay=a.delay) if a.cmd == 'crawl' else (lambda x: x if x else None)(c.execute('select status, sha256 from live where url=?', (url,)).fetchone())
        if r is None or r[0] != 200:
            print(json.dumps(dict(stop=url, status=r and r[0])), flush=True)
            break
        raw = c.execute('select raw_zlib from live where url=?', (url,)).fetchone()[0]
        doc = json.loads(zlib.decompress(raw))
        page = doc['_embedded']['searchResult']['page']
        total = page['totalPages']
        rows += records(doc, url, r[1])
        n += 1
        if n % 10 == 0:
            print(json.dumps(dict(pages=n, of=total, rows=len(rows))), flush=True)
        if n >= total or (a.limit_pages and n >= a.limit_pages):
            break
    if a.cmd == 'parse':
        out = Path(a.out) if a.out else P.data_w('ecommons-phd.json', KEY)
        out.write_text(json.dumps(dict(school=KEY, source='eCommons REST API discover/search/objects', query=QUERY, rows=rows), indent=1, ensure_ascii=False))
        print(json.dumps(dict(rows=len(rows), out=str(out))))
    else:
        print(json.dumps(dict(pages=n, of=total, rows=len(rows))))


if __name__ == '__main__':
    main(sys.argv[1:])
