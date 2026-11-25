"""The personal-homepage link on a PI's official unit profile page (PKU cs, sai, ai, icst/wict, cfcs, coe profiles; any host).

Chinese unit profiles print the link as a labelled field, 个人主页：<url> (the URL is plain text or an anchor whose text is the address, not a word), so
the anchor-text rule of person_websites_cn.link_kind never sees it (PKU websites audit 2026-11-25: 9 of 50 rows said no_web_presence while the
official profile named a homepage). This module reads the visible text and the anchors of a stored profile page and returns the labelled links.

  profile_homepage_links(html, base) -> [{'url', 'label', 'quote'}]    (pure; no network)
  candidates(school)                 -> {pi: [{'url', 'label', 'quote', 'profile_url', 'profile_sha256'}]} from the stored profile captures
  python -I tools/profile_homepage_links.py <school> [--out FILE]

A link counts only when an official profile of the PI itself prints it under a homepage label; a name pattern never makes a URL.
"""
import json
import re
import sys
import zlib
from urllib.parse import urljoin, urlsplit

LABEL = r'(?:个人主页|个人网站|个人网页|个人页面|个人主頁|个人首页|课题组主页|实验室主页|课题组网站|主\s*页|Personal\s+(?:Home\s*page|Web\s*(?:site|page)|Site|Page)|Home\s*page|Web\s*site)'
ASCII_URL = r"[A-Za-z0-9._~:/?#@!$&*+,;=%\-]+"   # a Han character ends the address (the next field label follows it without a space)
URL = r'(?:https?:)?//' + ASCII_URL + r'|www\.' + ASCII_URL
TEXT_RX = re.compile(r'(' + LABEL + r')\s*[:：]?\s*(' + URL + ')', re.I)
SKIP_HOST = re.compile(r'(?:^|\.)(?:scholar\.google\.[a-z.]+|linkedin\.com|twitter\.com|x\.com|facebook\.com|orcid\.org|dblp\.org|researchgate\.net|'
                       r'semanticscholar\.org|mailto)$', re.I)


def _norm(u, base):
    u = u.strip().rstrip('/.,;')
    if not re.match(r'(?:https?:)?//|/|\.|#', u) and re.match(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?:/|$)', u) and not re.search(r'\.(?:html?|php|aspx?|jsp)$', u.split('/')[0]):
        u = 'http://' + u   # a bare host written as an href ('lcs.ios.ac.cn/~znj/') is not relative to the profile
    if u.startswith('www.'):
        u = 'http://' + u
    try:
        return urljoin(base or 'http://', u)
    except ValueError:
        return ''


def profile_homepage_links(content, base=''):
    """Labelled personal-homepage links of one profile page: the label's text field (also in a meta description) and anchors that follow a label."""
    from bs4 import BeautifulSoup
    if isinstance(content, (bytes, bytearray)):
        try:
            content = zlib.decompress(content)
        except zlib.error:
            pass
        content = bytes(content).decode('utf-8', 'replace')
    soup = BeautifulSoup(content, 'html.parser')
    out, seen = [], set()

    def add(url, label, quote):
        url = _norm(url, base)
        host = urlsplit(url).hostname or ''
        key = host + urlsplit(url).path.rstrip('/') + ('?' + urlsplit(url).query if urlsplit(url).query else '')
        if not host or SKIP_HOST.search(host) or key in seen:
            return
        seen.add(key)
        out.append(dict(url=url, label=re.sub(r'\s+', '', label), quote=' '.join(quote.split())[:160]))

    meta = [m.get('content') or '' for m in soup.find_all('meta', attrs={'name': re.compile('^description$', re.I)})]
    for m in soup.find_all(['script', 'style']):
        m.decompose()
    text = ' '.join(soup.get_text(' ', strip=True).split())
    for src in [text] + meta:
        for m in TEXT_RX.finditer(src):
            add(m.group(2), m.group(1), src[max(0, m.start() - 10):m.end() + 10])
    for a in soup.find_all('a', href=True):   # an anchor right after the label, or an anchor whose own text is the label
        txt = ' '.join(a.get_text(' ', strip=True).split())
        prev = ''.join(str(s) for s in list(a.previous_siblings)[:2][::-1])
        prev = ' '.join(re.sub(r'<[^>]+>', ' ', prev).split())
        if re.fullmatch(LABEL + r'\W*', txt, re.I) or re.search(LABEL + r'\s*[:：]?\s*$', prev, re.I):
            href = a['href']
            if href.startswith('mailto:') or href.startswith('#') or href.startswith('javascript'):
                continue
            add(href, txt if re.fullmatch(LABEL + r'\W*', txt, re.I) else prev[-10:], f'{prev[-20:]} {txt}')
    return out


def profile_pages(school):
    """{pi: [(profile url, sha256, content)]}: the official profile pages recorded for each PI (person-websites pi_profile rows) from the stored captures."""
    import sqlite3

    import atlas_paths as P
    from lab_websites import capture_stores
    rows = json.loads(P.data('person-websites.json', school).read_text())['rows']
    want = {}
    for r in rows:
        if r.get('kind') == 'pi_profile' and r.get('url'):
            want.setdefault(r['person'], []).append((r['url'], r.get('sha256')))
    out = {}
    for path in capture_stores(school):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for pi, lst in want.items():
            for u, sha in lst:
                row = con.execute('select content from captures where sha256=? and content is not null limit 1', (sha,)).fetchone() if sha else None
                row = row or con.execute('select content, sha256 from captures where url=? and status=200 and content is not null order by id desc limit 1', (u,)).fetchone()
                if row:
                    out.setdefault(pi, []).append((u, sha or (row[1] if len(row) > 1 else None), row[0]))
    return out


def candidates(school):
    import hashlib
    res = {}
    for pi, pages in profile_pages(school).items():
        for u, sha, content in pages:
            body = content
            try:
                body = zlib.decompress(content)
            except zlib.error:
                pass
            for c in profile_homepage_links(body, u):
                res.setdefault(pi, []).append(dict(c, profile_url=u, profile_sha256=sha or hashlib.sha256(bytes(body)).hexdigest()))
    return res


def main(argv):
    school = argv[1]
    cands = candidates(school)
    out = json.dumps(cands, ensure_ascii=False, indent=1)
    if '--out' in argv:
        open(argv[argv.index('--out') + 1], 'w').write(out + '\n')
    print(school, len(cands), 'PIs with a labelled homepage link on a stored profile')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
