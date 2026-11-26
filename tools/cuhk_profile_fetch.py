"""CUHK stage 3 (2026-11-25): read the official department profile each unrecorded website PI's faculty-directory card links, live
(robots, pacing and challenge handling by labpage_audit.Kit), and add it to the register row as a dated `school_profile` check, so
`lab_websites.py enrich` can recover the profile -> website link from cached HTML. No Wayback, no reviewed decisions.
usage: cuhk_profile_fetch.py <register.json>   (rewrites the register in place)"""
import datetime
import json
import re
import sys
import unicodedata
import zlib
from urllib.parse import urljoin

import labpage_audit as L
from bs4 import BeautifulSoup

SCHOOL = 'cuhk'


def norm(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return sorted(re.findall(r'[a-z]+', text.casefold()))


def card_profile(html, base, pi):
    """The 'Personal Website' (department profile) href inside the directory card whose people-name carries exactly this PI's name tokens."""
    soup = BeautifulSoup(html, 'html.parser')
    want = norm(pi)
    for wrap in soup.select('div.people-wrap'):
        name = wrap.select_one('.people-name-wrap')
        if not name or norm(re.sub(r',\s*JP$', '', name.get_text(' ', strip=True))) != want:
            continue
        a = wrap.select_one('.people-website a[href]')
        if a:
            return urljoin(base, a['href'])
    return None


def main(path):
    doc = json.load(open(path))
    kit = L.Kit(SCHOOL)
    pages = {}
    n = 0
    for r in doc['labs']:
        if r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded':
            continue
        for c in r['checks']:
            if c.get('source') != 'department_listing' or c.get('result') != 'ok':
                continue
            page, _ = kit.stored(c['url'])
            if not page or not page.get('content'):
                continue
            html = page['content']
            try:
                html = zlib.decompress(html)
            except (zlib.error, TypeError):
                pass
            prof = card_profile(html, c['url'], r['pi'])
            if not prof:
                continue
            got = kit.get(prof, wb=False)
            status = got.get('status') or got.get('http_status')
            print(json.dumps(dict(pi=r['pi'], profile=prof, status=status, error=got.get('error'))), flush=True)
            r['checks'].append(dict(source='school_profile', url=prof, at=datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
                                    result=L.result_of(got), sha256=got.get('sha256'), listed_on=c['url']))
            n += 1
            break
    json.dump(doc, open(path, 'w'), indent=1, ensure_ascii=False)
    print('profiles fetched', n)


if __name__ == '__main__':
    main(sys.argv[1])
