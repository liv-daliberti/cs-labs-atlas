"""Website sweep for a staged (PI-only) school: every PI's profile / home / lab page and every lab-member page a lab's own people page links.

Staged schools have PIs and some websites (Codex's top-25 work) but no paper or student packages, so this reads the reviewed PI roster,
Codex's website verification (where each URL was linked from, with the linking page's sha256) and fetches live, politely
(tools/staged_fetch.py), to find what the official pages link. No student or membership relation is created.

  staged_websites.py build <school> [--workers 12] [--deadline SECONDS] [--out-dir DIR]
  staged_websites.py summary <school>
  staged_websites.py sample <school> [--seed N] [--n 30]

Rows (reviewed/person-websites.json, the person_websites.py format):
  kind pi_profile | pi_home | group | member_home      (a lab's own site is also in lab-websites.json; a PI's site is repeated here)
  found_from  {kind: official_page|lab_page|own_page|codex_register, url, sha256, anchor}: the page that links the URL
  fetched     true with sha256/status/fetched_at when this pass fetched the URL; otherwise false with a reason
              ('host not fetchable (robots/login)', 'queued: ...', 'not fetched: robots.txt disallows', 'host refused automated access ...')
  member_home rows carry role_as_stated (the heading text the people page shows above the link, verbatim) and anchor (the link text).
A URL counts only when an official page, or the lab's own page, links it; a name pattern is never a source.
"""
import argparse
import collections
import concurrent.futures as cf
import html
import json
import random
import re
import sys
import time
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

import atlas_paths as P
import person_websites as PW
import staged_fetch as SF

SCRATCH = P.ROOT / 'scratch' / 'websites-c'
ROLES = P.ROOT / 'scratch' / 'top25-roles-students-1107' / 'pi-role-verification.json'
SITES = P.ROOT / 'scratch' / 'top25-labs-20261107' / 'website-verification.json'

SOCIAL = PW.NOT_FETCHABLE
SKIP_HOST = re.compile(r'(?:^|\.)(?:github\.com|gitlab\.com|dl\.acm\.org|ieeexplore\.ieee\.org|arxiv\.org|doi\.org|youtube\.com|youtu\.be|'
                       r'openreview\.net|wikipedia\.org|ieee\.org|acm\.org|aaas\.org|nature\.com|science\.org|nsf\.gov|medium\.com|bsky\.app|apple\.com|google\.com|goo\.gl|bit\.ly|mastodon\.[a-z.]+|'
                       r'deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu|sites\.google\.com/site/)$', re.I)
SKIP_EXT = re.compile(r'\.(?:pdf|jpe?g|png|gif|svg|zip|gz|tar|pptx?|docx?|xlsx?|mp4|mov|bib|txt|css|js|ico)$', re.I)
HOME_TEXT = re.compile(r'home\s?page|web\s?site|web\s?page|personal (?:page|site)|my (?:page|site|home)|^home$', re.I)
WEAK_TEXT = re.compile(r'\b(?:lab|laboratory|research group|group)\b', re.I)
LAB_WORD = re.compile(r'\b(?:lab|laboratory|group|center|centre|institute|team|initiative|consortium)\b', re.I)
PEOPLE_TEXT = re.compile(r'^(?:people|members?|team|students?|group members?|lab members?|current (?:members|students)|our team|the team|'
                         r'who we are|researchers|lab people|group|alumni|phd students|graduate students|people & alumni)$', re.I)
PEOPLE_HREF = re.compile(r'(?:people|members?|team|students|group)(?:\.html?|/|$)', re.I)
ROLE_HEAD = re.compile(r'ph\.?\s?d|doctoral|graduate|students?\b|post-?docs?|postdoctoral|master|\bm\.?s\.? |undergrad|intern|visiting (?:student|scholar|researcher)|'
                       r'alumni|alumnus|former (?:members|students|group)|(?:current|group|lab|team) members|^members|^people|^team|researchers|'
                       r'research (?:assistants|staff|scientists)|staff|^graduated', re.I)
HEAD_NOT = re.compile(r'paper|award|publication|best|news|directory|conference|journal|talk|teaching|collaborat|view |administrative|professor|'
                      r'faculty|course|class|seminar|workshop|funding|sponsor|openings|prospective|apply|join', re.I)
NAME_STOP = {'visiting', 'austin', 'antonio', 'industry', 'engagement', 'san', 'cra', 'dreu', 'home', 'page', 'website', 'web', 'pdf', 'slides', 'paper', 'papers', 'cv', 'email', 'github', 'scholar', 'google', 'read', 'more',
             'here', 'see', 'link', 'publications', 'research', 'people', 'members', 'team', 'news', 'contact', 'teaching', 'lab', 'group',
             'university', 'department', 'school', 'institute', 'center', 'centre', 'college', 'projects', 'project', 'software', 'code',
             'data', 'dataset', 'about', 'join', 'us', 'openings', 'courses', 'course', 'student', 'students', 'alumni', 'former', 'current',
             'prof', 'professor', 'dr', 'ph', 'd', 'phd', 'visit', 'apply', 'blog', 'talks', 'awards', 'service', 'misc', 'previous',
             'computer', 'science', 'engineering', 'artificial', 'intelligence', 'machine', 'learning', 'systems', 'security', 'theory',
             'vision', 'language', 'natural', 'processing', 'robotics', 'graphics', 'networks', 'database', 'databases', 'software',
             'journal', 'conference', 'transactions', 'proceedings', 'society', 'association', 'award', 'awards', 'program', 'programs', 'fellows', 'fellowship', 'postdoctoral', 'workshop', 'symposium', 'review', 'press', 'magazine', 'council', 'foundation', 'overview', 'resources', 'tutorial', 'tutorials', 'seminar', 'seminars', 'events', 'event', 'funding', 'sponsors', 'and', 'the', 'of'}
NAME_TOKEN = re.compile(r"^(?:[A-Z][a-zà-ÿ'’\-]+|[A-Z]\.?|[A-Z][A-Z\-]+|de|van|von|der|den|di|da|del|la|le|bin|al|el|ibn)$")
CJK_NAME = re.compile(r'^[一-鿿]{2,4}$')
TITLEISH = re.compile(r'^(?:dr\.?|prof\.?|professor|mr\.?|ms\.?|mrs\.?)\s+', re.I)


def fold(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z0-9 ]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).split()


def looks_like_name(t):
    t = TITLEISH.sub('', (t or '').strip().strip(',;:'))
    if CJK_NAME.match(t):
        return t
    toks = t.split()
    if not 2 <= len(toks) <= 5 or len(t) > 45:
        return None
    if any(x.lower().strip('.,') in NAME_STOP for x in toks) or any(c.isdigit() for c in t):
        return None
    if not all(NAME_TOKEN.match(x.strip(',')) for x in toks):
        return None
    return t


def reg_domain(host):
    p = (host or '').lower().split('.')
    return '.'.join(p[-3:] if len(p) >= 3 and p[-2] in ('ac', 'edu', 'co', 'com') and len(p[-1]) == 2 else p[-2:])


def canon(u):
    u = urldefrag(u)[0]
    sp = urlsplit(u)
    return sp._replace(netloc=sp.netloc.lower(), path=sp.path if sp.path else '/').geturl()


class Page(HTMLParser):
    """Anchors with the nearest heading above them, the nearest name-looking text in the same block, the title and the h1."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.links, self.title, self.h1 = base, [], '', ''
        self._in, self._buf, self.heading, self.block_name = None, [], '', None
        self._a = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self._skip += 1
        if tag == 'base' and a.get('href'):
            self.base = urljoin(self.base, a['href'])
        if tag in ('li', 'tr', 'p', 'div', 'td', 'article', 'section'):
            self.block_name = None
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title', 'strong', 'b', 'dt', 'th', 'summary'):
            self._in, self._buf = tag, []
        if tag == 'a' and a.get('href'):
            self._a = [a['href'], []]

    def handle_data(self, data):
        if self._skip:
            return
        if self._in:
            self._buf.append(data)
        if self._a is not None:
            self._a[1].append(data)
        else:
            t = ' '.join(data.split())
            if t and looks_like_name(t):
                self.block_name = looks_like_name(t)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self._skip:
            self._skip -= 1
        if tag == self._in:
            t = ' '.join(''.join(self._buf).split())
            if tag == 'title' and not self.title:
                self.title = t
            elif tag == 'h1' and not self.h1:
                self.h1 = t
            if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt', 'th', 'summary') and t:
                self.heading = t
            elif tag in ('strong', 'b') and t and len(t) < 45 and ROLE_HEAD.search(t) and not looks_like_name(t):
                self.heading = t
            self._in = None
        if tag == 'a' and self._a is not None:
            href, parts = self._a
            self._a = None
            text = ' '.join(''.join(parts).split())
            try:
                url = urljoin(self.base, href)
            except ValueError:
                return
            if urlsplit(url).scheme in ('http', 'https'):
                self.links.append(dict(url=url, text=text, heading=self.heading, block_name=self.block_name))


def parse(body, base):
    p = Page(base)
    try:
        p.feed(body.decode('utf-8', 'replace'))
    except Exception:  # noqa: BLE001
        pass
    return p


def roster(school):
    """[dict(pi, profile_url, listing_url, listing_sha, role)] from the newest reviewed PI list."""
    if school == 'oxford':
        pis = json.loads(P.data('pis.json', school).read_text())
        reg = {r['pi']: r for r in json.loads(P.data('lab-websites.json', school).read_text())['labs']}
        out = []
        for p in pis:
            r = reg.get(p['pi']) or {}
            prof = next((c for c in r.get('checks') or [] if c.get('source') == 'school_profile' and c.get('result') in ('ok', 'ok_wayback')), None)
            lst = (p.get('listings') or [{}])[-1]
            out.append(dict(pi=p['pi'], profile_url=prof['url'] if prof else None, listing_url=lst.get('url'), listing_sha=lst.get('sha256'),
                            role=p.get('title')))
        return out
    rows = [x for x in json.loads(ROLES.read_text()) if x['school'] == school and x['role_status'] == 'verified_PI_role']
    have = {x['name'] for x in rows}
    add = P.data('census-additions.json', school)
    if add.exists():
        for x in json.loads(add.read_text()):
            if x.get('is_pi') and x['name'] not in have:
                s = (x.get('sources') or [{}])[0]
                rows.append(dict(name=x['name'], profile_url=x.get('profile_url'), source_url=s.get('url'), source_sha256=s.get('sha256'),
                                 role_as_listed=x.get('title_as_listed')))
    return [dict(pi=x['name'], profile_url=x.get('profile_url'), listing_url=x.get('source_url'), listing_sha=x.get('source_sha256'),
                 role=x.get('role_as_listed')) for x in rows]


def codex_sites(school):
    out = collections.defaultdict(list)
    for x in json.loads(SITES.read_text()):
        if x['school'] == school:
            for c in x.get('checks') or []:
                out[x['name']].append(c)
    return out


def row(person, role, lab, kind, url, ff, g=None, names=None, **extra):
    host = urlsplit(url).hostname or ''
    r = dict(person=person, role=role, lab=lab, kind=kind, url=url, found_from=ff)
    if PW.BANNED.search(host):
        r.update(fetched=False, fetch_reason='host not used (owner-banned source)')
    elif SOCIAL.search(host):
        r.update(fetched=False, fetch_reason='host not fetchable (robots/login)')
    elif g and g.get('status') == 200:
        r.update(fetched=True, fetched_at=g['at'], status=200, sha256=g['sha256'], final_url=g['final_url'] if g['final_url'] != url else None)
        if names is not None:
            r['names_person'] = names[0]
            if names[1]:
                r['name_quote'] = names[1]
    elif g and g.get('note') and not g['note'].startswith('deadline'):
        r.update(fetched=False, fetch_reason=g['note'] if g['status'] is None or g['status'] in (999,) else f"HTTP {g['status']}: {g['note'] or 'not a page'}",
                 status=g['status'])
        if g['status'] in (999,) or 'refused' in (g['note'] or ''):
            r['wayback_queue'] = True
    elif g and g.get('status') not in (None, 200):
        r.update(fetched=False, fetch_reason=f"HTTP {g['status']}", status=g['status'])
    else:
        r.update(fetched=False, fetch_reason='queued: not fetched in this pass (deadline); read live where robots allows, else Wayback only')
    r.update({k: v for k, v in extra.items() if v is not None})
    return r


def build(school, workers=12, deadline=None, fetch_members=True):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    fx = SF.Fetcher(SCRATCH / f'{school}.sqlite', deadline=(time.time() + deadline) if deadline else None)
    ros = roster(school)
    cx = codex_sites(school) if school != 'oxford' else {}
    pool = cf.ThreadPoolExecutor(workers)

    def getall(urls):
        urls = list(dict.fromkeys(urls))
        return dict(zip(urls, pool.map(fx.get, urls)))

    # 1. directory listing pages (profile fallback) and profile pages
    dirs = getall([r['listing_url'] for r in ros if r['listing_url'] and not r['profile_url']])
    for r in ros:
        if not r['profile_url'] and r['listing_url'] in dirs and dirs[r['listing_url']]['status'] == 200:
            g = dirs[r['listing_url']]
            toks = fold(r['pi'])
            for lk in parse(g['body'], g['final_url']).links:
                t = fold(lk['text'])
                if len(toks) >= 2 and t and set(t) == set(toks) and urlsplit(lk['url']).hostname == urlsplit(g['final_url']).hostname:
                    r['profile_url'], r['profile_found_on'] = canon(lk['url']), dict(url=r['listing_url'], sha256=g['sha256'], anchor=lk['text'])
                    break
    profs = getall([r['profile_url'] for r in ros if r['profile_url']])
    # site chrome: links that recur on many profile pages
    cnt = collections.Counter()
    parsed = {}
    for u, g in profs.items():
        if g['status'] == 200:
            parsed[u] = parse(g['body'], g['final_url'])
            cnt.update({canon(lk['url']) for lk in parsed[u].links})
    chrome = {u for u, n in cnt.items() if n >= max(4, 0.2 * len(parsed))}

    # 2. candidate home / lab / third-party pages per PI
    cands = collections.defaultdict(dict)   # pi -> url -> dict(ff, anchor)
    for r in ros:
        pi, g = r['pi'], profs.get(r['profile_url'])
        for c in cx.get(pi, []):
            u = c.get('requested_url') or c.get('url')
            if u and not PW.BANNED.search(urlsplit(u).hostname or ''):
                cands[pi].setdefault(canon(u), dict(ff=dict(kind='official_page', url=c.get('source_url'), sha256=c.get('source_sha256'),
                                                           via='codex website verification: ' + c.get('discovery', '')), anchor=None,
                                                  codex_status=c.get('status')))
        if g and g['status'] == 200 and r['profile_url'] in parsed:
            me = reg_domain(urlsplit(g['final_url']).hostname)
            for lk in parsed[r['profile_url']].links:
                u = canon(lk['url'])
                host = urlsplit(u).hostname or ''
                if u in chrome or u == canon(g['final_url']) or SKIP_EXT.search(urlsplit(u).path) or PW.BANNED.search(host):
                    continue
                if SOCIAL.search(host):
                    if re.search(r'scholar\.google|linkedin|twitter|x\.com|researchgate|orcid|dblp|semanticscholar', host):
                        cands[pi].setdefault(u, dict(ff=dict(kind='official_page', url=r['profile_url'], sha256=g['sha256'], anchor=lk['text']),
                                                     anchor=lk['text'], social=True))
                    continue
                if SKIP_HOST.search(host):
                    continue
                same = reg_domain(host) == me
                if re.search(r'(?i)/(?:publications?|pubs?|papers?|cv|resume|teaching|courses?)(?:\.html?)?/?$', urlsplit(u).path):
                    continue
                strong = bool(HOME_TEXT.search(lk['text'] or ''))
                weak = bool(WEAK_TEXT.search(lk['text'] or '')) and (same or len((lk['text'] or '').split()) <= 3)
                if strong or weak or ('~' in urlsplit(u).path and same):
                    if same and re.search(r'/(?:people|research|faculty|about|academics?|news|events?)/?(?:index\.html?)?$', urlsplit(u).path):
                        continue
                    cands[pi].setdefault(u, dict(ff=dict(kind='official_page', url=r['profile_url'], sha256=g['sha256'], anchor=lk['text']),
                                                 anchor=lk['text']))
        if school == 'oxford':
            reg = {x['pi']: x for x in json.loads(P.data('lab-websites.json', school).read_text())['labs']}.get(pi) or {}
            for ev in reg.get('official_link_evidence') or []:
                if ev.get('url'):
                    cands[pi].setdefault(canon(ev['url']), dict(ff=dict(kind='official_page', url=ev.get('on'), sha256=ev.get('source_sha256'),
                                                                        anchor=ev.get('anchor'), via='existing Oxford lab register'), anchor=ev.get('anchor')))
            if reg.get('url') and reg.get('coverage') == 'website':
                o = (reg.get('official_link_evidence') or [{}])[0]
                cands[pi].setdefault(canon(reg['url']), dict(ff=dict(kind='official_page', url=o.get('on'), sha256=o.get('source_sha256'),
                                                                     anchor=o.get('anchor'), via='existing Oxford lab register'), anchor=o.get('anchor')))
    for pi in cands:   # a department or university front page is not a person's or lab's site
        roots = {urlsplit(r_['profile_url']).hostname for r_ in ros if r_['profile_url']}
        for u in [u for u in cands[pi] if urlsplit(u).path in ('', '/') and not urlsplit(u).query and urlsplit(u).hostname in roots]:
            del cands[pi][u]
    fetch_urls = [u for pi in cands for u, c in cands[pi].items() if not c.get('social')]
    sites = getall(fetch_urls)

    # 3. classify, then find the lab's people pages and members
    rows, labs, members_todo = [], [], []
    for r in ros:
        pi = r['pi']
        g = profs.get(r['profile_url'])
        if r['profile_url'] and g:
            ff = (dict(kind='official_page', url=r['profile_found_on']['url'], sha256=r['profile_found_on']['sha256'], anchor=r['profile_found_on']['anchor'])
                  if r.get('profile_found_on') else dict(kind='official_page', url=r['listing_url'], sha256=r['listing_sha']))
            rows.append(row(pi, 'pi', pi, 'pi_profile', r['profile_url'], ff, g, profile_type='official', role_as_listed=r['role']))
        else:
            rows.append(dict(person=pi, role='pi', lab=pi, kind='pi_profile', url=None,
                             reason='the reviewed PI roster gives no individual profile link for this PI and the directory listing page has no link '
                                    'anchored on the name; no profile found' ))
        toks = fold(pi)
        home_rows = []
        for u, c in cands[pi].items():
            if c.get('social'):
                rows.append(row(pi, 'pi', pi, 'pi_profile', u, c['ff'], profile_type='third_party', anchor=c['anchor']))
                continue
            g = sites.get(u)
            named = (False, None)
            title = h1 = ''
            if g and g['status'] == 200:
                body_t = ' '.join(fold(html.unescape(re.sub(r'<[^>]+>', ' ', g['body'][:400000].decode('utf-8', 'replace')))))
                named = (len(toks) >= 2 and toks[0] in body_t.split() and toks[-1] in body_t.split(), None)
                pg = parse(g['body'], g['final_url'])
                title, h1 = pg.title, pg.h1
            head = ' '.join([title, h1, c.get('anchor') or ''])
            has_name = bool(toks) and len(toks) >= 2 and toks[-1] in fold(head)
            lab_like = bool(LAB_WORD.search(head))
            if g and g['status'] == 200 and not named[0] and c.get('codex_status') != 'verified_website':
                note = 'linked from the official profile page; the page does not state the PI\'s name'
            else:
                note = None
            kind = 'group' if (lab_like and not has_name) else 'pi_home'
            rr = row(pi, 'pi', pi, kind, u, c['ff'], g, named, anchor=c.get('anchor'), page_title=title or None, h1=h1 or None, note=note,
                     codex_status=c.get('codex_status'))
            rows.append(rr)
            home_rows.append(rr)
            if g and g['status'] == 200 and (named[0] or c.get('codex_status') == 'verified_website'):
                members_todo.append((pi, u, g))
        site = next((x for x in home_rows if x['kind'] == 'group' and x['fetched']), None) or next((x for x in home_rows if x['fetched']), None) \
            or (home_rows[0] if home_rows else None)
        if home_rows:
            labs.append(dict(pi=pi, url=site['url'], coverage='website', kind='lab_site' if site['kind'] == 'group' else 'pi_homepage',
                             found_from=site['found_from'], fetched=site['fetched'], sha256=site.get('sha256'), names_person=site.get('names_person'),
                             other_urls=[x['url'] for x in home_rows if x is not site]))
        else:
            reason = ('profile page fetched; it links no personal, lab or group site (non-navigation anchors checked), and Codex\'s website '
                      'verification found none' if g and g['status'] == 200 else
                      'profile page could not be fetched (%s) and Codex\'s website verification found no site' % ((g or {}).get('note') or 'no profile URL'))
            rows.append(dict(person=pi, role='pi', lab=pi, kind='pi_home', url=None, reason=reason))
            labs.append(dict(pi=pi, url=None, coverage='reason', reason=reason + '; no lab list entry; no own page linked from any official page'))

    # 4. people pages and member links
    people_pages = []
    for pi, u, g in members_todo:
        pg = parse(g['body'], g['final_url'])
        host = urlsplit(g['final_url']).hostname
        pp = []
        for lk in pg.links:
            if urlsplit(lk['url']).hostname == host and canon(lk['url']) != canon(g['final_url']) and not SKIP_EXT.search(urlsplit(lk['url']).path) \
                    and (PEOPLE_TEXT.match(lk['text'] or '') or (not lk['text'] and PEOPLE_HREF.search(urlsplit(lk['url']).path))):
                pp.append((canon(lk['url']), lk['text']))
        for u2, t in list(dict.fromkeys(pp))[:3]:
            people_pages.append((pi, u, g, u2, t))
    pgs = getall([x[3] for x in people_pages])
    seen_members = set()
    mrows = []
    sources = [(pi, g['final_url'], g, None) for pi, u, g in members_todo] + [(pi, pgs[u2]['final_url'], pgs[u2], t) for pi, u, g, u2, t in people_pages
                                                                              if pgs[u2]['status'] == 200]
    for pi, src_url, g, via in sources:
        pg = parse(g['body'], g['final_url'])
        host = urlsplit(g['final_url']).hostname
        pi_toks = set(fold(pi))
        for lk in pg.links:
            u = canon(lk['url'])
            lhost = urlsplit(u).hostname or ''
            if u == canon(g['final_url']) or SKIP_EXT.search(urlsplit(u).path) or PW.BANNED.search(lhost) or (SKIP_HOST.search(lhost) and not SOCIAL.search(lhost)):
                continue
            name = looks_like_name(lk['text'])
            via_block = False
            if not name and lk['block_name'] and (HOME_TEXT.search(lk['text'] or '') or re.match(r'(?i)^(?:web ?page|homepage|home|website|personal|site|link)$', lk['text'] or '')):
                name, via_block = lk['block_name'], True
            if not name or not ROLE_HEAD.search(lk['heading'] or '') or HEAD_NOT.search(lk['heading'] or '') or len(lk['heading']) > 70:
                continue
            if set(fold(name)) <= pi_toks:
                continue
            key = (pi, name, u)
            if key in seen_members:
                continue
            seen_members.add(key)
            mrows.append((pi, name, u, g, lk, via_block))
    roster_keys = {tuple(fold(r['pi'])[:1] + fold(r['pi'])[-1:]) for r in ros}
    mfetch = getall([m[2] for m in mrows if not SOCIAL.search(urlsplit(m[2]).hostname or '')]) if fetch_members else {}
    for pi, name, u, g, lk, via_block in mrows:
        mg = mfetch.get(u)
        named = (False, None)
        if mg and mg['status'] == 200:
            toks = fold(name)
            body_t = ' '.join(fold(html.unescape(re.sub(r'<[^>]+>', ' ', mg['body'][:400000].decode('utf-8', 'replace')))))
            named = (len(toks) >= 2 and toks[0] in body_t.split() and toks[-1] in body_t.split(), None)
        fn = fold(name)
        rows.append(row(name, 'member', pi, 'member_home', u,
                        dict(kind='lab_page', url=g['final_url'], sha256=g['sha256'], anchor=lk['text']), mg, named,
                        role_as_stated=lk['heading'], anchor=lk['text'], name_from='adjacent text in the same list entry' if via_block else 'link text',
                        same_site=(urlsplit(u).hostname == urlsplit(g['final_url']).hostname) or None,
                        is_roster_pi=True if len(fn) >= 2 and any(fn[0] == r_[0] and fn[-1] == r_[-1] for r_ in roster_keys) else None))
    doc = dict(school=school, tool='tools/staged_websites.py', review_status='automatic',
               source='scratch/top25-roles-students-1107/pi-role-verification.json (verified_PI_role), scratch/top25-labs-20261107/website-verification.json, live fetch',
               generated=time.strftime('%Y-%m-%d'), rows=rows)
    return doc, dict(school=school, tool='tools/staged_websites.py', review_status='automatic', labs=labs)


def counts(doc):
    c = collections.Counter()
    for r in doc['rows']:
        k = f"{r['role']}:{r['kind']}"
        c[k + (':url' if r['url'] else ':reason')] += 1
        if r['url']:
            c[k + (':fetched' if r['fetched'] else ':unfetched')] += 1
            if 'not fetchable' in r.get('fetch_reason', ''):
                c[k + ':host_not_fetchable'] += 1
            if r.get('wayback_queue'):
                c[k + ':wayback_queue'] += 1
    return dict(sorted(c.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['build', 'summary', 'sample'])
    ap.add_argument('school')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--deadline', type=int, default=3000)
    ap.add_argument('--out-dir', help='directory that receives person-websites.json and lab-websites.json (default: this worktree)')
    ap.add_argument('--seed', type=int, default=20261108)
    ap.add_argument('--n', type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out_dir) if a.out_dir else Path(__file__).resolve().parents[1] / 'hierarchy' / a.school / 'reviewed'
    pw, lw = out / 'person-websites.json', out / 'lab-websites.json'
    if a.cmd == 'build':
        doc, labs = build(a.school, a.workers, a.deadline)
        out.mkdir(parents=True, exist_ok=True)
        pw.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
        labs_path = lw if a.school != 'oxford' else out / 'lab-websites-sweep.json'
        labs_path.write_text(json.dumps(labs, indent=1, ensure_ascii=False) + '\n')
    doc = json.loads(pw.read_text())
    bad = PW.gate(doc)
    if a.cmd == 'sample':
        pool = [r for r in doc['rows'] if r['url']]
        for r in random.Random(a.seed).sample(pool, min(a.n, len(pool))):
            print(json.dumps(r, ensure_ascii=False))
    else:
        print(a.school, json.dumps(counts(doc)), 'gate_problems', len(bad))
    for b in bad[:5]:
        print('  !', b, file=sys.stderr)
    return int(bool(bad))


if __name__ == '__main__':
    sys.exit(main())
