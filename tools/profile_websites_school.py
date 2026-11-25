"""Own-website links on a PI's school profile card (KAIST CS card: `웹사이트 <a href>`), for stage 5 identity (D-0064: an identifier, not a name match).

usage: profile_websites_school.py <key>

For each census PI whose profile page is stored (live table), the external website the card itself links is recorded in reviewed/extra-lab-pages.json
(`{name: [{url, why, source_url, sha256}]}`; existing entries are kept). periods_school.targets() then fetches it (live), homepage_links_school.py reads its
DBLP/ORCID links, and dblp_ids_school.py treats it as the PI's homepage (a DBLP record that links the same URL binds). Nothing is fetched here.
"""
import json
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

LABELS = re.compile(r'웹사이트|홈페이지|website|homepage', re.I)
SKIP = re.compile(r'kaist\.ac\.kr/people/|mailto:|javascript:|linkedin|facebook|twitter|x\.com|youtube', re.I)


def card_website(html):
    """The external URL of the card's website field (dt label, dd link), else None."""
    soup = BeautifulSoup(html, 'html.parser')
    for dt in soup.find_all('dt'):
        if LABELS.search(dt.get_text(' ', strip=True)):
            dd = dt.find_next_sibling('dd')
            a = dd.find('a', href=True) if dd else None
            if a and a['href'].startswith('http') and not SKIP.search(a['href']):
                return a['href'].strip()
    return None


def same_host_redirect(c, url):
    """The Location of a stored 3xx answer of `url` when it stays on the same host (scheme upgrade, www., a path move); a redirect to another host is never followed
    (school_web records it as needing a policy review)."""
    from urllib.parse import urljoin, urlsplit
    row = c.execute('select status, raw_zlib from live where url=?', (url,)).fetchone()
    if not row or not (300 <= (row[0] or 0) < 400) or not row[1]:
        return None
    try:
        loc = json.loads(zlib.decompress(row[1])).get('location')
    except ValueError:
        return None
    if not loc:
        return None
    loc = urljoin(url, loc)
    host = lambda u: urlsplit(u).netloc.lower().removeprefix('www.')   # noqa: E731
    return loc if host(loc) == host(url) and loc != url else None


def main(key):
    census = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    c = W.con(key)
    f = P.data('extra-lab-pages.json', key)
    out = json.loads(f.read_text()) if f.exists() else {}
    n = added = 0
    for p in census:
        if not p.get('is_pi') or not p.get('profile_url'):
            continue
        row = c.execute('select status, sha256, raw_zlib from live where url=?', (p['profile_url'],)).fetchone()
        if not row or row[0] != 200 or not row[2]:
            continue
        n += 1
        url = card_website(zlib.decompress(row[2]).decode('utf-8', 'replace'))
        if url and url not in {e['url'] if isinstance(e, dict) else e for e in out.get(p['name'], [])}:
            out.setdefault(p['name'], []).append(dict(url=url, why="the website field of the PI's own school profile card", source_url=p['profile_url'], sha256=row[1]))
            added += 1
    followed = 0
    for nm, es in out.items():   # one hop on the same host, recorded as its own page with the reason
        for e in list(es):
            tgt = same_host_redirect(c, e['url'] if isinstance(e, dict) else e)
            if tgt and tgt not in {x['url'] if isinstance(x, dict) else x for x in es}:
                es.append(dict(url=tgt, why='same-host redirect target of ' + (e['url'] if isinstance(e, dict) else e), source_url=e.get('source_url') if isinstance(e, dict) else None))
                followed += 1
    P.data_w('extra-lab-pages.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(cards=n, websites_added=added, redirects_followed=followed, pis_with_website=len(out))))


if __name__ == '__main__':
    main(sys.argv[1])
