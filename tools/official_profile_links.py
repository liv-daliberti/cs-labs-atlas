"""The homepage an OFFICIAL unit profile or listing links for each PI (stage 3 websites; HKUST rework 2026-11-25, USTC/WHU 2026-11-25).

A department profile that carries a "Personal Webpage" / "Personal Homepage" / "Homepage" anchor names the PI's own site; that address,
never the profile itself, a unit root or an office page, is the PI's website, with a dated official-link check. This tool reads the
profiles and writes the reviewed input the register builder (lab_websites.py) consumes:

  hierarchy/<key>/reviewed/profile-links.json
    {school, tool, generated, rows: [{pi, profile_url, fetched_at, status, sha256, artifact, link: {url, anchor, quote} | null,
                                      source: 'profile' | 'listing', note}]}
  the page bytes: hierarchy/<key>/reviewed/identity-sources/<sha256>.html (force-added, like the other retained source bytes)

Rules: robots.txt is honoured (a disallowed host is never fetched; the row says so and carries no link, so no site is invented);
at least 3 s between requests to a host; no login, paywall or bot challenge; one row per PI. A profile that answers an error and has
no archived copy has `link` null and its status says why: that is not a statement that no homepage exists.

Per school: `configure(key)` derives the unit-root / office-host / unit-page rules from the charter's [web].domains (HKUST keeps its own hand rules).
HKUST rows define the site (the first homepage anchor of the profile). Every other school's rows only CONFIRM a site the register already holds
(`confirms`): the official page must link exactly that address, and the profile candidates are the register's own department_listing /
school_profile check URLs plus the census profile_url (labels may be Chinese: 个人主页, 个人网页, 主页, 个人网站, Homepage). A page that links no such address
gets status `read_no_matching_link`, never an absence: lab_websites.confirm_profile_links records only the links that were found.

usage: official_profile_links.py <school> [--pi NAME ...] [--only-missing] [--not-recorded]
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

import atlas_paths as P  # noqa: E402

ZH_LABEL = r'(?:个人|课题组|实验室|团队|研究组)?(?:主页|网页|网站)(?:链接|地址)?|个人(?:简介)?主页'   # 个人主页, 个人网页, 个人网站, 主页, 课题组主页 ... (never 首页: that is a site's own home button)
LINK_TEXT = re.compile(r'^\s*(?:personal\s*)?(?:home\s*page|web\s*page|web\s*site|website|webpage|homepage)\s*$|^\s*personal\s+(?:home\s*page|web\s*page|web\s*site|site)\s*$|^\s*(?:' + ZH_LABEL + r')\s*[:：>»]?\s*$', re.I)
ATTR_TEXT = re.compile(r'^\s*personal\s+(?:web\s*address|web\s*page|home\s*page|website|site)\s*$', re.I)
TEXT_LINK = re.compile(r'Personal\s+(?:Webpage|Homepage|Home\s*Page|Website)\s+(https?://\S+)|(?:个人(?:主页|网页|网站))\s*[:：]?\s*(https?://[\x21-\x7e]+)', re.I)
IDENTITY_INDEX = re.compile(r'(?:scholar\.google|orcid\.org|scopus\.com|dblp\.org|linkedin\.com|researchgate\.net|webofscience|publons|github\.com/[^/]+/?$|facebook|twitter)', re.I)   # an untitled link to one of these is no homepage
ANCHOR = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.I | re.S)
HREF = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.I)
UA = 'Mozilla/5.0 (compatible; research-atlas-bot)'
GAP = 3.0
HOST_GAP = {'researchportal.hkust.edu.hk': 5.5}   # its robots.txt asks for Crawl-Delay: 5
SKIP_SCHEME = re.compile(r'^(?:javascript|mailto|tel|#)', re.I)
NEVER_FETCH = re.compile(r'(?:^|\.)facultyprofiles\.[a-z0-9.-]+$', re.I)   # owner/coordinator ruling 2026-11-25: robots-disallowed per discovery; never fetched
UNIT_ROOTS = re.compile(r'^(?:www\.)?(?:hkust\.edu\.hk|ust\.hk)$|^(?:provost|hkustprovost)\.hkust\.edu\.hk$', re.I)
OFFICE_HOST = re.compile(r'(?:^|\.)(?:provost|hkustprovost|president|library|hr|ito)\.(?:hkust\.edu\.hk|ust\.hk)$', re.I)   # an office site is no personal homepage
SCHOOL = dict(key='hkust', domain=None)   # configure() swaps these for another school's charter-derived rules
PERSONAL_HOST = re.compile(r'^(?:staff|faculty|jszy|home|people|homepage|teacher|teachers|web|personal)[.-]', re.I)   # a faculty-space or personal host: a site, not a unit page


def configure(key):
    """Derive the unit-root, office-host and unit-page rules from the school's charter ([web].domains). HKUST keeps its hand-written rules."""
    global UNIT_ROOTS, OFFICE_HOST
    SCHOOL.update(key=key, domain=None)
    if key == 'hkust':
        return
    import school_config as SC
    doms = [d.lower() for d in SC.field(SC.get(key), 'web.domains', []) or []]
    if not doms:
        raise SystemExit(f'schools/{key}.toml has no [web].domains')
    alt = '|'.join(re.escape(d) for d in doms)
    SCHOOL['domain'] = re.compile(rf'(?:^|\.)(?:{alt})$', re.I)
    UNIT_ROOTS = re.compile(rf'^(?:www\.)?(?:{alt})$', re.I)
    OFFICE_HOST = re.compile(rf'(?:^|\.)(?:provost|president|library|lib|hr|ito|news|jwc|yjs)\.(?:{alt})$', re.I)


def text_of(fragment):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', fragment or '')).strip()


def homepage_anchors(html, base):
    """[(absolute url, anchor text)] of the anchors whose own text says homepage/personal webpage; never a bare unit root or the base page itself."""
    out = []
    for m in ANCHOR.finditer(html or ''):
        h = HREF.search(m.group(1))
        label = text_of(m.group(2))
        if not LINK_TEXT.match(label):   # an icon link names itself in aria-label/title ("Personal web address")
            attr = re.search(r'(?:aria-label|title)\s*=\s*["\']([^"\']+)["\']', m.group(1), re.I)
            label = attr.group(1).strip() if attr and ATTR_TEXT.match(attr.group(1)) else label
        if not h or not (LINK_TEXT.match(label) or ATTR_TEXT.match(label)) or SKIP_SCHEME.match(h.group(1).strip()):
            continue
        url = urllib.parse.urljoin(base, h.group(1).strip()).split('#')[0]
        parts = urllib.parse.urlsplit(url)
        if url.rstrip('/') == base.rstrip('/') or (UNIT_ROOTS.match(parts.hostname or '') and parts.path in ('', '/')) or OFFICE_HOST.search(parts.hostname or ''):
            continue
        out.append((url, label))
    if not out:   # CSE profile pages print the address as text after the label: 'Personal Webpage https://amir.goharshady.com/'
        for m in TEXT_LINK.finditer(text_of(html)):
            url = (m.group(1) or m.group(2)).rstrip('.,;)')
            parts = urllib.parse.urlsplit(url)
            if url.rstrip('/') != base.rstrip('/') and not (UNIT_ROOTS.match(parts.hostname or '') and parts.path in ('', '/')):
                out.append((url, 'Personal Webpage'))
    return list(dict.fromkeys(out))


GAP_TAGS = r'(?:[^<>]|<[^>]*>){0,60}'


def name_regexes(names):
    """Case-insensitive patterns for a person's names in a listing, given-family or family-given with markup between the tokens."""
    pats = []
    for n in names:
        t = [x for x in re.split(r'[\s,]+', re.sub(r'[()]', ' ', n)) if x]
        if re.search('[A-Za-z]', n) and len(t) >= 2:
            a, b = ('[- ]?'.join(re.escape(x) for x in t[0].split('-')), '[- ]?'.join(re.escape(x) for x in t[-1].split('-')))   # 'Chi-Ying' also reads 'Chi Ying' and 'ChiYing'
            pats.append(re.compile(f'{a}{GAP_TAGS}{b}|{b}{GAP_TAGS}{a}', re.I))
        elif not re.search('[A-Za-z]', n) and len(n.strip()) >= 2:
            pats.append(re.compile(re.escape(n.strip())))
    return pats


CARD = re.compile(r'class="[^"]*\b(?:team-item|people-item|views-row|person|faculty-item|member)\b[^"]*"', re.I)


def listing_hit(html, names, window=2500):
    """(profile href or None, block): where the PI's name first appears in the visible part of a unit listing, the profile link around it
    and the slice from the name to the end of that person's card (the next card marker, at most `window` characters)."""
    html = re.sub(r'<script.*?</script>|<style.*?</style>', '', html or '', flags=re.S)
    for rx in name_regexes(names):
        m = rx.search(html)
        if not m:
            continue
        before = html[max(0, m.start() - 400):m.start()]
        a = before.rfind('<a ')
        href = None
        if a >= 0 and '</a>' not in before[a:]:
            h = HREF.search(before[a:])
            href = h.group(1).strip() if h else None
        tail = html[m.start():m.start() + window]
        nxt = CARD.search(tail, 40)
        blk = tail[:nxt.start()] if nxt else tail
        if href is None:
            near = [(abs(h.start() - 400), h.group(1)) for h in re.finditer(r'href\s*=\s*["\']([^"\']*profile/[^"\']+)["\']', html[max(0, m.start() - 400):m.start() + 600])]
            if near:
                href = min(near)[1]
        if href is None:
            first = ANCHOR.search(blk)
            if first:
                h = HREF.search(first.group(1))
                href = h.group(1).strip() if h else None
        return href, blk
    return None, ''


def json_nodes(html, names):
    """For a Drupal listing that embeds each person as a JSON node (ECE people_list): (profile path alias, [(uri, title)]) of the node whose
    title carries the PI's name; the links are the node's own `field_reference_link` entries."""
    if '"nid":[' not in (html or ''):
        return None
    pats = name_regexes([n for n in names if re.search('[A-Za-z]', n)])
    for chunk in html.split('"nid":[')[1:]:
        t = re.search(r'"title":\[\{"value":"([^"]*)"', chunk)
        if not t:
            continue
        title = json.loads('"' + t.group(1) + '"') if '\\u' in t.group(1) else t.group(1)
        if not any(rx.search(title) for rx in pats):
            continue
        links = []
        k = chunk.find('"field_reference_link":')
        if k >= 0:
            try:
                arr, _ = json.JSONDecoder().raw_decode(chunk[k + len('"field_reference_link":'):])
                links = [(e.get('uri'), e.get('title') or ('Personal Homepage' if e.get('uri') and not IDENTITY_INDEX.search(e['uri']) else '')) for e in arr]
            except ValueError:
                links = []
        al = re.search(r'"alias":"([^"]+)"', chunk)
        return (json.loads('"' + al.group(1) + '"') if al else None), links
    return None


class Fetcher:
    def __init__(self):
        self.robots, self.last = {}, {}

    def allowed(self, url):
        p = urllib.parse.urlsplit(url)
        if NEVER_FETCH.search(p.hostname or ''):
            return False
        base = f'{p.scheme}://{p.netloc}'
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + '/robots.txt')
            try:
                req = urllib.request.Request(base + '/robots.txt', headers={'User-Agent': UA})
                body = urllib.request.urlopen(req, timeout=30).read().decode('utf8', 'ignore')
                rp.parse(body.splitlines())
                # a group that names an AI crawler is honoured too (standing rule)
                for agent in ('ClaudeBot', 'anthropic-ai', 'Claude-Web'):
                    if not rp.can_fetch(agent, url):
                        self.robots[base] = False
                        return False
            except Exception:  # noqa: BLE001 (no readable robots.txt: no restriction)
                rp = None
            self.robots[base] = rp
        rp = self.robots[base]
        return True if rp in (None, True) else (False if rp is False else rp.can_fetch(UA, url))

    def get(self, url):
        host = urllib.parse.urlsplit(url).netloc
        wait = HOST_GAP.get(host, GAP) - (time.time() - self.last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.time()
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60)
            return r.status, r.read(), r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, b'', url
        except Exception as e:  # noqa: BLE001
            return str(e)[:60], b'', url


AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web')


def robots_rule(body, url, agents=AI_AGENTS + ('*',)):
    """(allowed, agent, rule line) for `url` from a robots.txt body: the longest matching Allow/Disallow of the first of `agents` that has a group
    (a group naming an AI crawler comes before the '*' group). None for the rule when nothing matches (allowed)."""
    path = urllib.parse.urlsplit(url).path or '/'
    if urllib.parse.urlsplit(url).query:
        path += '?' + urllib.parse.urlsplit(url).query
    groups, cur, collecting = [], None, False
    for raw in (body or '').splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        k = k.lower()
        if k == 'user-agent':
            if not collecting:
                cur = dict(agents=[], rules=[])
                groups.append(cur)
            cur['agents'].append(v.lower())
            collecting = True
        elif k in ('allow', 'disallow') and cur is not None:
            collecting = False
            cur['rules'].append((k, v))
    for agent in agents:
        g = next((g for g in groups if agent.lower() in g['agents']), None)
        if g is None:
            continue
        best = None
        for k, v in g['rules']:
            if v == '' and k == 'disallow':
                continue
            pat = re.escape(v).replace(r'\*', '.*').replace(r'\$', '$')
            if re.match(pat, path) and (best is None or len(v) > len(best[1]) or (len(v) == len(best[1]) and k == 'allow')):
                best = (k, v)
        if best is None:
            return True, agent, None
        return best[0] == 'allow', agent, f'{best[0].capitalize()}: {best[1]}'
    return True, None, None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def robots_check(f, url):
    """The dated robots evidence for `url` (only /robots.txt is requested, redirects are not followed): {host, robots_url, checked_at, status,
    error, sha256, allowed, agent, rule}. The project's policy (labpage_audit Kit._ai_allowed): permission is a 200 robots.txt whose rules (a group
    naming an AI crawler first) allow the path, or a 404/410; a redirect, a server error, a TLS failure or no answer is no usable permission."""
    p = urllib.parse.urlsplit(url)
    robots_url = f'{p.scheme}://{p.netloc}/robots.txt'
    host = p.netloc
    wait = HOST_GAP.get(host, GAP) - (time.time() - f.last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    f.last[host] = time.time()
    st, body, err = None, b'', None
    try:
        r = urllib.request.build_opener(_NoRedirect).open(urllib.request.Request(robots_url, headers={'User-Agent': UA}), timeout=30)
        st, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        st = e.code
    except Exception as e:  # noqa: BLE001
        err = str(e)[:120]
    checked = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime())
    text = body.decode('utf8', 'ignore') if body and st == 200 else ''
    if st == 200 and '<html' not in text[:500].lower():
        allowed, agent, rule = robots_rule(text, url)
        verdict = 'allowed' if allowed else 'refused'   # an explicit Disallow rule of a readable robots.txt
    elif st in (404, 410):
        allowed, agent, rule, verdict = True, None, None, 'allowed'
    else:   # a redirect, a server error, a TLS failure, no answer or an HTML stub: not permission, and not a Disallow either
        allowed, agent, rule, verdict = False, None, f'no usable robots.txt ({st if st else err})', 'no_usable_permission'
    return dict(host=host, robots_url=robots_url, checked_at=checked, status=st, error=err, sha256=hashlib.sha256(body).hexdigest() if body else None,
                allowed=allowed, verdict=verdict, agent=agent, rule=rule)


def wayback(f, url, years=('', '2022', '2020', '2024', '2018'), want=None):
    """An archived copy (id_ bytes) of `url`: the closest to each year in turn (newest first), the first for which `want(bytes)` holds;
    None when no copy exists or none satisfies `want`. Each request is paced by the caller's fetcher."""
    seen = set()
    for y in years:
        api = 'https://archive.org/wayback/available?url=' + urllib.parse.quote(url, safe='') + (f'&timestamp={y}0601' if y else '')
        st, body, _ = f.get(api)
        try:
            snap = json.loads(body)['archived_snapshots'].get('closest')
        except Exception:  # noqa: BLE001
            snap = None
        if not snap or str(snap.get('status')) != '200' or snap['timestamp'] in seen:
            continue
        seen.add(snap['timestamp'])
        ts = snap['timestamp']
        orig = 'http' + snap['url'].split('/http', 1)[1]
        time.sleep(3)
        st, pg, _ = f.get(f'https://web.archive.org/web/{ts}id_/{orig}')
        if pg and (want is None or want(pg)):
            return ts, f'https://web.archive.org/web/{ts}id_/{orig}', pg
    return None


def UNIT_PAGE(url):
    if SCHOOL['domain'] is not None:   # charter-derived: a host of the school's domains that is not a faculty-space or personal host
        p = urllib.parse.urlsplit(url)
        return bool(SCHOOL['domain'].search(p.hostname or '')) and not PERSONAL_HOST.match(p.hostname or '') and '~' not in p.path
    return hkust_unit_page(url)


def hkust_unit_page(url):
    """True for an HKUST unit's own profile/directory page (not a personal ~user or people.ust.hk site): the page a link must be followed through."""
    p = urllib.parse.urlsplit(url)
    h = p.hostname or ''
    if not re.search(r'(?:^|\.)(?:hkust\.edu\.hk|ust\.hk)$', h) or re.search(r'(?:^|\.)people\.ust\.hk$|\.home\.ece\.ust\.hk$', h) or '~' in p.path:
        return False
    return bool(re.search(r'/profile/|/people/|/faculty/|/faculty-and-staff/|/directory/', p.path) or (re.fullmatch(r'/[^/]+/?', p.path) and h.startswith('ece.')))


def portal_slugs(names):
    """The research portal's person slugs for a PI's Latin names (given-family, with middle names): researchportal.hkust.edu.hk/en/persons/<slug>/."""
    import unicodedata
    out = []
    for n in names:
        if not re.search('[A-Za-z]', n):
            continue
        t = [re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower())
             for x in re.split(r'[\s,]+', re.sub(r'[()]', ' ', n)) if re.search('[A-Za-z]', x)]
        t = [x for x in t if x]
        if len(t) >= 2:
            out += ['-'.join([t[0], t[-1]]), '-'.join(t)]
    return list(dict.fromkeys(out))[:4]


def portal_link(f, names):
    """(portal url, bytes, link) of the first research-portal person page that answers for these names and shows a 'Personal web address', else None."""
    for slug in portal_slugs(names):
        u = f'https://researchportal.hkust.edu.hk/en/persons/{slug}/'
        if not f.allowed(u):
            return None
        st, data, fin = f.get(u)
        if data and st == 200:
            links = [(a, b) for a, b in homepage_anchors(data.decode('utf8', 'ignore'), u) if not IDENTITY_INDEX.search(a)]
            return u, data, (links[0] if links else None)
    return None


def save(school, data):
    sha = hashlib.sha256(data).hexdigest()
    d = Path(P.data('profile-links.json', school)).parent / 'identity-sources'
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{sha}.html').write_bytes(data)
    return sha, f'hierarchy/{school}/reviewed/identity-sources/{sha}.html'


CHALLENGE = re.compile(r'\$_ts\b|_\$ts|ruishu|tlsCaptcha|cf-challenge|Just a moment', re.I)   # Ruishu / Cloudflare interstitials: discarded, never stored
PROFILE_LIKE = re.compile(r'/page\.htm$|/info/\d+/\d+\.htm|/article/\d+|view\.php\?aid=|teacherinfo\.aspx|/Faculty/|/szdw/[^/]+/\d{6}/', re.I)
WAYBACK_FORM = re.compile(r'^wayback\s+(\d{14})\s+(\S+)$')   # how the census spells an archived source: 'wayback 20250325040012 cs.ustc.edu.cn/fjs_23239/list2.htm'


def live_form(url):
    """The original address behind a census/register source spelling (an archive playback URL, 'wayback TS host/path', or a plain URL); None if neither."""
    url = (url or '').strip()
    m = WAYBACK_FORM.match(url)
    if m:
        return 'http://' + m.group(2)
    url = re.sub(r'^https?://web\.archive\.org/web/\d+[a-z_]*/', '', url)
    return re.sub(r':(?:80|443)(?=/)', '', url) if url.startswith('http') else None


def profile_candidates(key, lab, crows):
    """Official pages of the school's domains that may link this PI's site: the register row's own department_listing / school_profile
    check URLs and the census profile_url / basis / source URLs, profile-shaped pages first. Never a personal-space or NEVER_FETCH host."""
    urls = [c.get('url') for c in lab.get('checks') or [] if c.get('source') in ('department_listing', 'school_profile')]
    for c in crows:
        pu = c.get('profile_url') or ''
        urls += [pu if pu.startswith('http') else None, (c.get('pi_basis') or {}).get('url')] + [z.get('url') for z in c.get('sources') or []]
    out = []
    for u in urls:
        u = live_form(u)
        host = urllib.parse.urlsplit(u or '').hostname or ''
        if u and SCHOOL['domain'].search(host) and not NEVER_FETCH.search(host) and u not in out and not (u.rstrip('/') == (lab.get('url') or '').rstrip('/')):
            out.append(u)
    return sorted(out, key=lambda u: not PROFILE_LIKE.search(u))


def find_expected(html, base, expected):
    """(url as linked, label) of the first anchor (or 'Personal Homepage http://...' text) on the page whose address is `expected`. The label must say
    homepage (Chinese labels included), except that a link from an official page to another page of the school's own domains counts under any label."""
    from lab_websites import normalized_link
    want = normalized_link(expected)
    own = bool(SCHOOL['domain'].search(urllib.parse.urlsplit(expected).hostname or ''))
    for m in ANCHOR.finditer(html or ''):
        h = HREF.search(m.group(1))
        if not h or SKIP_SCHEME.match(h.group(1).strip()):
            continue
        url = urllib.parse.urljoin(base, h.group(1).strip()).split('#')[0]
        if normalized_link(url) != want:
            continue
        label = text_of(m.group(2)) or (re.search(r'(?:title|aria-label)\s*=\s*["\']([^"\']+)', m.group(1)) or [None, ''])[1].strip()
        if LINK_TEXT.match(label) or ATTR_TEXT.match(label) or (own and label):
            return url, label
    for url, label in homepage_anchors(html, base):
        if normalized_link(url) == want:
            return url, label
    return None


def confirm_school(key, a):
    """Non-HKUST schools: for each selected register row with a site and no recorded official link, read its candidate official pages (live; a 403/challenge host
    or an unreadable page goes to the newest archived copy) and record the page that links exactly the registered address. Row field `confirms` = that address."""
    pis = {x['pi']: x for x in json.loads(Path(P.data('pis.json', key)).read_text())}
    census = {x['name']: x for x in json.loads(Path(P.data('census-faculty.json', key)).read_text())['faculty']}
    adds = {x['name']: x for x in json.loads(Path(P.data('census-additions.json', key)).read_text())}
    reg = json.loads(Path(a.register or P.data('lab-websites.json', key)).read_text())
    out_path = Path(P.data('profile-links.json', key))
    doc = json.loads(out_path.read_text()) if out_path.exists() else dict(school=key, tool='tools/official_profile_links.py', rows=[])
    rows = {r['pi']: r for r in doc['rows']}
    f = Fetcher()
    from lab_websites import normalized_link
    pages, denied = {}, set()
    pool = []
    for lab_ in reg['labs']:
        nm = [lab_['pi']] + [n for n in (pis.get(lab_['pi']) or {}).get('names') or []]
        pool += [u for u in profile_candidates(key, lab_, [c for n in nm for c in [census.get(n) or adds.get(n)] if c]) if not PROFILE_LIKE.search(u)]
    pool = list(dict.fromkeys(pool))
    now = lambda: time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime())  # noqa: E731

    def read(url):
        """(status, bytes, capture_url) for a candidate page: live first unless its host already refused us, then the archive."""
        host = urllib.parse.urlsplit(url).netloc
        if url not in pages:
            pages[url] = None
            if host not in denied and f.allowed(url):
                st, data, _ = f.get(url)
                if st == 200 and data and not CHALLENGE.search(data[:200000].decode('utf8', 'ignore')):
                    pages[url] = ('ok', data, None)
                elif st in (403, 429, 202, 412) or (data and CHALLENGE.search(data[:200000].decode('utf8', 'ignore'))):
                    denied.add(host)
            if pages[url] is None and not NEVER_FETCH.search(host):
                wb = wayback(f, url, want=lambda b: not CHALLENGE.search(b[:200000].decode('utf8', 'ignore')))
                if wb:
                    pages[url] = ('ok_wayback', wb[2], wb[1])
        return pages[url]

    for lab in reg['labs']:
        pi = lab['pi']
        if lab.get('coverage') != 'website' or not lab.get('url') or lab.get('official_link_status') == 'recorded':
            continue
        if (a.pi and pi not in a.pi) or ((a.only_missing or a.not_recorded) and pi in rows and rows[pi].get('link')):
            continue
        names = [pi] + [n for n in (pis.get(pi) or {}).get('names') or [] if n != pi]
        crows = [c for n in names for c in [census.get(n) or adds.get(n)] if c]
        cands = profile_candidates(key, lab, crows)
        row = dict(pi=pi, profile_url=None, fetched_at=now(), status='no_profile_candidate', sha256=None, artifact=None, link=None, source='profile',
                   note=None, confirms=lab['url'], tried=[])

        def scan(urls, limit, tried):
            """Read the pages in turn (a listing's own `listN.htm` pagination is followed); stop at the first that links the registered address."""
            queue, seen, n = list(urls), set(), 0
            while queue and n < limit:
                url = queue.pop(0)
                if normalized_link(url) in seen:
                    continue
                seen.add(normalized_link(url))
                n += 1
                pg = read(url)
                if not pg:
                    if tried is not None:
                        tried.append(dict(url=url, status='unreadable'))
                    continue
                status, data, capture = pg
                sha, art = save(key, data)
                html = data.decode('utf8', 'ignore')
                hit = find_expected(html, url, lab['url'])
                if tried is not None:
                    tried.append(dict(url=url, status=status, sha256=sha))
                if hit or tried is not None:   # a pool page that links nothing is not this PI's profile: it leaves the row alone
                    row.update(profile_url=url, status=status if hit else 'read_no_matching_link', sha256=sha, artifact=art, fetched_at=now(), capture_url=capture)
                    if not capture:
                        row.pop('capture_url')
                if hit:
                    row['link'] = dict(url=hit[0], anchor=hit[1], quote=hit[1])
                    return True
                d = url.rsplit('/', 1)[0]
                queue = [urllib.parse.urljoin(url, h) for h in dict.fromkeys(re.findall(r'href="([^"]*list\d+\.htm)"', html)) if urllib.parse.urljoin(url, h).rsplit('/', 1)[0] == d] + queue
            return False

        if not scan(cands, a.max_pages, row['tried']):   # the unit's own pages first, then every other official listing of the school (read once, cached)
            scan([u for u in pool if u not in cands], 400, None)
        if row['status'] == 'no_profile_candidate' and cands:
            row['status'] = 'unreadable'
        rows[pi] = row
        print(pi, '|', row['status'], '|', row['profile_url'], '|', (row['link'] or {}).get('url'), flush=True)
        doc['rows'] = list(rows.values())
        out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('school')
    ap.add_argument('--pi', nargs='*')
    ap.add_argument('--only-missing', action='store_true')
    ap.add_argument('--not-recorded', action='store_true', help='non-HKUST: only register rows whose official link is not recorded (the default selection)')
    ap.add_argument('--register', help='non-HKUST: the register to read the rows from (default: the installed lab-websites.json)')
    ap.add_argument('--max-pages', type=int, default=4, help='non-HKUST: candidate official pages read per PI')
    a = ap.parse_args()
    key = a.school
    configure(key)
    if key != 'hkust':
        return confirm_school(key, a)
    pis = json.loads(Path(P.data('pis.json', key)).read_text())
    census = {x['name']: x for x in json.loads(Path(P.data('census-faculty.json', key)).read_text())['faculty']}
    adds = {x['name']: x for x in json.loads(Path(P.data('census-additions.json', key)).read_text())}
    out_path = Path(P.data('profile-links.json', key))
    doc = json.loads(out_path.read_text()) if out_path.exists() else dict(school=key, tool='tools/official_profile_links.py', rows=[])
    rows = {r['pi']: r for r in doc['rows']}
    f = Fetcher()
    robots_cache = {}

    def attach_robots(row):
        """The dated robots evidence of the host the profile links (a unit page is read, not judged here): only /robots.txt is requested."""
        if row['link'] and not UNIT_PAGE(row['link']['url']):
            hostkey = urllib.parse.urlsplit(row['link']['url']).netloc
            if hostkey not in robots_cache:
                robots_cache[hostkey] = robots_check(f, row['link']['url'])
            row['link_robots'] = robots_cache[hostkey]
    listings = {}
    now = lambda: time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime())  # noqa: E731
    for x in pis:
        pi = x['pi']
        if (a.pi and pi not in a.pi) or (a.only_missing and pi in rows):
            continue
        names = [pi] + [n for n in x.get('names') or [] if n != pi]
        latin = [n for n in names if re.search('[A-Za-z]', n)]
        crows = []   # every census row of the merged person (a CSE row and an ECE addition for the same professor)
        for n_ in names:
            cr = census.get(n_) or adds.get(n_)
            if cr and cr not in crows:
                crows.append(cr)
        unwb = lambda u: re.sub(r':(?:80|443)(?=/)', '', re.sub(r'^https?://web\.archive\.org/web/\d+[a-z_]*/', '', u or ''))  # noqa: E731
        okhost = lambda u: not NEVER_FETCH.search(urllib.parse.urlsplit(u).hostname or '')  # noqa: E731
        cands, src_urls = [], []
        for c in crows:
            pu = c.get('profile_url')
            basis_url = (c.get('pi_basis') or {}).get('url') or ''
            srcs = [unwb(u) for u in [basis_url] + [x_.get('url') for x_ in c.get('sources') or []] if u]
            src_urls += srcs
            if pu and not pu.startswith('http'):
                host = urllib.parse.urlsplit(srcs[0] if srcs else '').netloc or 'cse.hkust.edu.hk'
                host = host.replace('www.cse.ust.hk', 'cse.hkust.edu.hk').replace('cse.ust.hk', 'cse.hkust.edu.hk')
                cands.append(f'https://{host}/admin/people/faculty/' + pu)
            elif pu:
                cands.append(unwb(pu))
            if basis_url and okhost(unwb(basis_url)) and not re.search(r'(people_list|/people/?$|faculty\.php|/faculty/?$|directory|\?d=textview|web\.archive\.org)', basis_url):
                cands.append(unwb(basis_url))
        cands = [u for u in dict.fromkeys(cands) if okhost(u)]
        listing = None
        if not cands:
            listing = next((u for u in src_urls if okhost(u)), None)
        row = dict(pi=pi, profile_url=None, fetched_at=now(), status='no_profile_candidate', sha256=None, artifact=None, link=None, source='profile', note=None)
        best = None
        for url in cands:
            row.update(profile_url=url, source='profile')
            if not f.allowed(url):
                row.update(status='robots_disallowed', note='host disallows fetching for our agent; not fetched')
                break
            st, data, final = f.get(url)
            if data and st == 200:
                sha, art = save(key, data)
                row.update(status='ok', sha256=sha, artifact=art, fetched_at=now())
            else:
                wb = wayback(f, url, want=lambda b: bool(homepage_anchors(b.decode('utf8', 'ignore'), url))) or wayback(f, url)
                if wb:
                    ts, wburl, pg = wb
                    sha, art = save(key, pg)
                    data = pg
                    row.update(status='ok_wayback', sha256=sha, artifact=art, capture_url=wburl, fetched_at=now())
                    final = url
                else:
                    row.update(status=f'http_{st}_no_archived_copy', note='the profile answers an error and no archived copy was found')
                    continue
            html = data.decode('utf8', 'ignore')
            links = homepage_anchors(html, row.get('capture_url') and re.sub(r'^https?://web\.archive\.org/web/\d+[a-z_]*/', '', row['capture_url']) or final)
            if not links and '"nid":[' in html:
                node = json_nodes(html, latin)
                hp = [(u, t) for u, t in (node[1] if node else []) if u and LINK_TEXT.match(t or '')]
                links = [(u, t) for u, t in hp]
            if not links and row['status'] == 'ok':   # a live profile that renders its links by script shows none: the newest archived copy is read too
                wb = wayback(f, url, want=lambda b: bool(homepage_anchors(b.decode('utf8', 'ignore'), url)))
                if wb:
                    ts, wburl, pg = wb
                    wl = homepage_anchors(pg.decode('utf8', 'ignore'), url)
                    if wl:
                        sha, art = save(key, pg)
                        row.update(status='ok_wayback', sha256=sha, artifact=art, capture_url=wburl, fetched_at=now(),
                                   note='the live profile shows no homepage link (rendered by script); the archived copy of ' + ts[:8] + ' does')
                        links = wl
            if links:
                u, label = links[0]
                row['link'] = dict(url=u, anchor=label, quote=label)
                break
            best = best or dict(row)
        if row['link'] is None and best is not None:
            row = best
        if row['link'] is None and listing and row['status'] in ('no_profile_candidate',):
            row['profile_url'], row['source'] = listing, 'listing'
            if not f.allowed(listing):
                row.update(status='robots_disallowed', note='listing host disallows fetching')
            else:
                if listing not in listings:
                    listings[listing] = f.get(listing)
                st, data, final = listings[listing]
                if data and st == 200:
                    sha, art = save(key, data)
                    html = data.decode('utf8', 'ignore')
                    node = json_nodes(html, latin)
                    if node is not None:
                        alias, nl = node
                        hp = [(u, t) for u, t in nl if u and LINK_TEXT.match(t or '')]
                        row.update(status='ok', sha256=sha, artifact=art, fetched_at=now(), profile_url=urllib.parse.urljoin(final, alias) if alias else listing, source='listing')
                        if hp:
                            row['link'] = dict(url=hp[0][0], anchor=hp[0][1], quote=hp[0][1])
                        attach_robots(row)
                        rows[pi] = row
                        print(pi, '|', row['status'], '|', row['profile_url'], '|', (row['link'] or {}).get('url'), flush=True)
                        doc['rows'] = [rows[p_['pi']] for p_ in pis if p_['pi'] in rows]
                        out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
                        continue
                    href, blk = listing_hit(html, latin + [n for n in names if not re.search('[A-Za-z]', n)])
                    row.update(status='ok' if blk else 'name_not_in_listing', sha256=sha, artifact=art, fetched_at=now())
                    links = homepage_anchors(blk, final)
                    prof = urllib.parse.urljoin(final, href) if href and not SKIP_SCHEME.match(href) else None
                    if prof and urllib.parse.urlsplit(prof).netloc and prof.rstrip('/') != final.rstrip('/') and not links:
                        # the listing names the PI and links the PI's own profile: that profile is the official source
                        if f.allowed(prof):
                            st2, d2, fin2 = f.get(prof)
                            if d2 and st2 == 200:
                                sha2, art2 = save(key, d2)
                                row.update(profile_url=prof, source='profile', status='ok', sha256=sha2, artifact=art2, fetched_at=now())
                                links = homepage_anchors(d2.decode('utf8', 'ignore'), fin2)
                        else:
                            row.update(profile_url=prof, status='robots_disallowed', note='profile host disallows fetching for our agent; not fetched')
                    if links:
                        u, label = links[0]
                        row['link'] = dict(url=u, anchor=label, quote=label)
                else:
                    row.update(status=f'http_{st}')
        if row['link'] is None and row['status'] != 'no_profile_candidate_and_denied':
            pl = portal_link(f, latin)
            if pl and pl[2]:
                sha_p, art_p = save(key, pl[1])
                row.update(profile_url=pl[0], source='portal', status='ok', sha256=sha_p, artifact=art_p, fetched_at=now(), capture_url=None,
                           note='the HKUST research portal person page links the personal web address', link=dict(url=pl[2][0], anchor=pl[2][1], quote=pl[2][1]))
            elif pl:
                row['portal_checked'] = dict(url=pl[0], sha256=save(key, pl[1])[0], result='no personal web address')
        lk = row['link']
        if lk and UNIT_PAGE(lk['url']) and f.allowed(lk['url']):
            # the profile links another unit page (a joint professor's other department, a directory entry): that page is read one hop further
            st3, d3, fin3 = f.get(lk['url'])
            if d3 and st3 == 200:
                sha3, art3 = save(key, d3)
                hop = homepage_anchors(d3.decode('utf8', 'ignore'), fin3)
                row['via_profile'] = dict(url=lk['url'], sha256=sha3, artifact=art3, fetched_at=now())
                row['link'] = dict(url=hop[0][0], anchor=hop[0][1], quote=hop[0][1]) if hop else None
        attach_robots(row)
        rows[pi] = row
        print(pi, '|', row['status'], '|', row['profile_url'], '|', (row['link'] or {}).get('url'), flush=True)
        doc['rows'] = [rows[p['pi']] for p in pis if p['pi'] in rows]
        out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
