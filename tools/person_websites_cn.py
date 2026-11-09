"""Person / lab website register for the staged Chinese top-25 schools (pku ustc whu uestc seu hit).

These schools have PIs and some websites but no paper or student packages (Codex's top25 staging), so the inputs are
the reviewed PI list and the staged captures, read-only, not hierarchy/<school>/pis.json:

  PI list      scratch/top25-goal-1107/progress-pi-detail.csv   (the newest reviewed PI list: school, PI, website, website_review)
  candidates   scratch/top25-labs-20261107/faculty-candidates.json   (name -> official_profile_url, source listing url + sha256)
  captures     scratch/top25-labs-20261107/hierarchy/<school>/raw/school-captures.sqlite   table live (url, status, sha256, raw_zlib)

  person_websites_cn.py build <school>        offline rows + a polite live pass (robots first, 2 attempts per URL) -> reviewed/person-websites.json
  person_websites_cn.py offline <school>      offline rows only
  person_websites_cn.py summary <school>
  person_websites_cn.py sample <school> [--seed N] [--n 30]

kind  pi_profile | pi_home | group | lab | pi_other | member_home.  `lab` is the PI-centred lab: url = the lab's own site
(same as the group row) or a reason.  member_home = a page linked from a lab's own people page, `role` verbatim as the page
states it (Chinese kept in the original script).  No student relations are produced.  A URL counts only when an official
page, the lab's own page or the person's own page links it; names are never turned into URLs.
"""
import argparse
import json
import random
import re
import sqlite3
import sys
import threading
import time
import urllib.parse
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import atlas_paths as P
import person_websites as W

SCRATCH = Path(P.ROOT) / 'scratch'
TOP25 = SCRATCH / 'top25-goal-1107'
LABS = SCRATCH / 'top25-labs-20261107'
OUT_CAP = SCRATCH / 'websites-d'
SCHOOLS = ('pku', 'ustc', 'whu', 'uestc', 'seu', 'hit')
NOW = time.strftime('%Y-%m-%d')
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory; robots.txt honoured)'

PEOPLE = re.compile(r'团队|成员|学生|人员|研究生|师生|课题组|研究组|实验室成员|people|member|team|student|alumni|lab\s*members|group', re.I)
LABTXT = re.compile(r'实验室|课题组|研究组|研究所|研究中心|工作室|Lab\b|Laboratory|Group\b|Center|Centre|Institute', re.I)
HOMETXT = re.compile(r'主页|主頁|个人网站|个人网页|个人页面|home\s*page|personal\s*(?:web)?(?:site|page)', re.I)
ORGTXT = re.compile(r'Working Group|Challenge|Conference|Workshop|Journal|Committee|Society|Association|IEEE|ACM|委员会|学会|协会|会议|期刊|研讨会|University\b|大学$', re.I)
SKIP_HREF = re.compile(r'^(?:javascript:|mailto:|tel:|#)|\.(?:pdf|docx?|pptx?|zip|rar|jpe?g|png|gif)(?:$|\?)', re.I)
PROFILE_LINK = re.compile(r'scholar\.google\.[a-z.]+/citations\?(?:[^#]*&)?user=|linkedin\.com/in/|(?:twitter|x)\.com/[A-Za-z0-9_]+/?$|orcid\.org/\d|dblp\.org/pid/|semanticscholar\.org/author/|researchgate\.net/profile/', re.I)
LATIN_NAV = re.compile(r'Information|Teaching|Research|Publication|News|People|Contact|Home\\b|About|Guideline|Career|Newcomer|Things|\\bLab\\b|Group|Team|Member|Student|Alumni|Faculty|Project|Course|Software|Data|Resource|Award|Talk|Position|Opportunit|Visiting|Scientist|Accessibility|Policy|Center|Centre|Institute|University|Learning|Network|Computing|Security|Intelligence', re.I)
NAME_CJK = re.compile(r'^[一-鿿·]{2,4}$')
NAME_LAT = re.compile(r"^[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}$")
ROLE_HEAD = re.compile(r'博士|硕士|研究生|本科|学生|教师|教授|老师|助理|博后|博士后|访问|毕业|在读|校友|成员|Ph\.?D|Master|Undergrad|Student|Postdoc|Alumni|Faculty|Member|Visiting|Staff|Intern', re.I)
NOT_NAME = {'更多', '详情', '返回', '首页', '联系', '联系我们', '关于我们', '研究方向', '研究成果', '团队介绍', '课题组', '师资队伍',
            '招生信息', '学生信息', '科学研究', '教学研究', '论文成果', '科研项目', '新闻动态', '实验室', '研究组', '更多>>', '公众号'}


def norm_name(s):
    return re.sub(r'\s+', '', s or '')


def norm_url(u):
    p = urllib.parse.urlsplit(u or '')
    path = re.sub(r'/(?:index\.(?:html?|jsp|php)|main\.htm)$', '/', p.path) if p.path else '/'
    return (p.hostname or '', path.rstrip('/'), p.query)


def decode(raw):
    for enc in ('utf-8', 'gb18030'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace')


def anchors(raw, base):
    return [(h.strip(), t) for h, t in W.page_anchors(decode(raw).encode('utf-8'), base)]


class Live:
    """Stored 'live' captures of the staged school + this tool's own fetches."""

    def __init__(self, school):
        self.pages = {}
        con = sqlite3.connect(f'file:{LABS}/hierarchy/{school}/raw/school-captures.sqlite?mode=ro', uri=True)
        for url, at, st, sha, blob in con.execute('select url, fetched_at, status, sha256, raw_zlib from live'):
            if 'web.archive.org' in url or (st and 300 <= st < 400) or (blob and zlib.decompress(blob)[:20].startswith(b'{"requested_url"')):
                continue    # staged redirect stubs carry no page; this tool fetches them live
            self.pages[url] = dict(at=at, status=st, sha256=sha, raw=zlib.decompress(blob) if blob else None, source='staged')
        self.robots = {h: (st, b) for h, st, b in con.execute('select host, status, body from robots')}
        self.own = OUT_CAP / f'{school}-captures.sqlite'
        OUT_CAP.mkdir(parents=True, exist_ok=True)
        c2 = sqlite3.connect(self.own)
        c2.execute('create table if not exists f (url text primary key, final_url text, at text, status int, sha256 text, raw blob, error text)')
        c2.execute('create table if not exists r (host text primary key, at text, status int, body text)')
        c2.commit()
        c2.close()
        self.load_own()

    def load_own(self):
        c2 = sqlite3.connect(self.own)
        for url, final, at, st, sha, blob, err in c2.execute('select url, final_url, at, status, sha256, raw, error from f'):
            self.pages[url] = dict(at=at, status=st, sha256=sha, raw=zlib.decompress(blob) if blob else None, source='own',
                                   final_url=final, error=err)
        for h, at, st, body in c2.execute('select host, at, status, body from r'):
            self.robots[h] = (st, body)
        c2.close()

    def find(self, url):
        if url in self.pages:
            return url, self.pages[url]
        k = norm_url(url)
        for u, v in self.pages.items():
            if norm_url(u) == k:
                return u, v
        return None, None


def page_title(raw):
    m = re.search(r'<title[^>]*>(.*?)</title>', decode(raw)[:20000], re.S | re.I)
    return ' '.join((m.group(1) if m else '').split())[:120]


class Fetcher:
    def __init__(self, school, live):
        self.school, self.live = school, live
        self.last = defaultdict(float)
        self.lock = threading.Lock()
        self.blocked = {}
        self.db = sqlite3.connect(live.own, check_same_thread=False)

    def delay_for(self, host):
        import urllib.robotparser
        st, body = self.live.robots.get(host, (None, None))
        rp = urllib.robotparser.RobotFileParser()
        rp.parse((body or '').splitlines() if st == 200 else [])
        return max(3.0, float(rp.crawl_delay('*') or 0), float(rp.crawl_delay(UA) or 0))

    def robots(self, url):
        import requests
        p = urllib.parse.urlsplit(url)
        host = p.netloc
        if host not in self.live.robots:
            st, body = None, ''
            for attempt in range(2):
                try:
                    r = requests.get(f'{p.scheme}://{host}/robots.txt', headers={'User-Agent': UA}, timeout=(8, 15))
                    st, body = r.status_code, r.text
                    break
                except Exception:
                    time.sleep(4)
            if st is None:
                st = -1
            with self.lock:
                self.live.robots[host] = (st, body)
                self.db.execute('insert or replace into r values (?,?,?,?)', (host, NOW, st, body))
                self.db.commit()
            time.sleep(2)
        st, body = self.live.robots[host]
        if st == -1 or (st is not None and st >= 500):
            return False, 'unreachable from our network (timeout): robots.txt not retrievable after 2 attempts'
        from school_web import robots_decision
        ours, ai, _ = robots_decision(st, body, url)
        if not ours:
            return False, 'robots.txt disallows this path'
        if not ai:
            return False, 'robots.txt names an AI agent (ClaudeBot/anthropic-ai/Claude-Web): host not used'
        return True, ''

    def get(self, url):
        """-> page dict or None; the result (also failures) is cached in the own capture db."""
        import requests
        u, v = self.live.find(url)
        if v is not None and (v.get('raw') or v.get('error')):
            return v
        host = urllib.parse.urlsplit(url).netloc
        ok, why = self.robots(url)
        if not ok:
            rec = dict(at=NOW, status=None, sha256=None, raw=None, source='own', error=why)
            self.store(url, rec)
            return rec
        if self.blocked.get(host, 0) >= 3:
            return dict(at=NOW, status=None, sha256=None, raw=None, source='own', error='host challenged or refused repeatedly: queued for Wayback only')
        delay = self.delay_for(host)
        err = None
        for attempt in range(2):
            with self.lock:
                wait = self.last[host] + delay - time.time()
                self.last[host] = max(time.time(), self.last[host]) + (delay if wait > 0 else 0)
            if wait > 0:
                time.sleep(wait)
            try:
                r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.5'}, timeout=(8, 25))
                self.last[host] = time.time()
                body = r.content[:3_000_000]
                if r.status_code in (403, 412, 429, 503) or re.search(rb'captcha|verify you are human|Just a moment', body[:4000], re.I):
                    self.blocked[host] = self.blocked.get(host, 0) + 1
                    rec = dict(at=NOW, status=r.status_code, sha256=None, raw=None, source='own',
                               error=f'HTTP {r.status_code} / challenge: not retried; queued for Wayback only', final_url=r.url)
                    self.store(url, rec)
                    return rec
                rec = dict(at=NOW, status=r.status_code, sha256=sha256(body).hexdigest(), raw=body, source='own', final_url=r.url, error=None)
                self.store(url, rec)
                return rec
            except Exception as e:  # timeout, reset, DNS, TLS
                err = type(e).__name__
                self.last[host] = time.time()
                time.sleep(5)
        rec = dict(at=NOW, status=None, sha256=None, raw=None, source='own',
                   error=f'unreachable from our network (timeout/{err}) after 2 attempts')
        self.store(url, rec)
        return rec

    def store(self, url, rec):
        with self.lock:
            self.db.execute('insert or replace into f values (?,?,?,?,?,?,?)',
                            (url, rec.get('final_url'), rec['at'], rec['status'], rec['sha256'],
                             zlib.compress(rec['raw']) if rec.get('raw') else None, rec.get('error')))
            self.db.commit()
        self.live.pages[url] = rec


def ff_page(url, rec, anchor=None):
    return dict(kind='official_page', url=url, sha256=rec.get('sha256'), **({'anchor': anchor} if anchor else {}))


def fetched_fields(url, rec):
    if rec is None:
        return dict(fetched=False, fetch_reason='queued: not fetched; read live where robots allows, else Wayback only')
    if rec.get('raw'):
        out = dict(fetched=True, fetched_at=rec['at'], status=rec['status'], sha256=rec['sha256'])
        if rec.get('final_url') and norm_url(rec['final_url']) != norm_url(url):
            out['final_url'] = rec['final_url']
        return out
    return dict(fetched=False, fetch_reason=rec.get('error') or 'not fetched', **({'status': rec['status']} if rec.get('status') else {}))


def inputs(school):
    rows = [r for r in __import__('csv').DictReader(open(TOP25 / 'progress-pi-detail.csv', encoding='utf-8')) if r['school'] == school]
    fc = defaultdict(list)
    for x in json.load(open(LABS / 'faculty-candidates.json')):
        if x['school'] == school:
            fc[norm_name(x['name'])].append(x)
    return rows, fc


def host_class(url):
    h = urllib.parse.urlsplit(url).hostname or ''
    if W.NOT_FETCHABLE.search(h):
        return 'host not fetchable (robots/login)'
    return None


def link_kind(text, url, home_host):
    """group | pi_home | None for an external link on a PI's page."""
    t = text or ''
    if ORGTXT.search(t):
        return None
    if LABTXT.search(t):
        return 'group'
    if HOMETXT.search(t):
        return 'pi_home'
    return None


ROLE_VOCAB = re.compile(r'^(?:博士后|博士生?|博士研究生|硕士生?|硕士研究生|研究生|本科生?|在读|已毕业|毕业生|校友|访问学生|访问学者|科研助理|实习生|Ph\\.?D|Master|M\\.?S|Undergrad|Postdoc|Alumni|Visiting|Intern|Research (?:Assistant|Scientist)|Past|Current|Former|Graduate)', re.I)


def role_of_headings(raw):
    """Yield (anchor_text, href, role) in document order; role = last heading-like text that names a role, verbatim."""
    import html.parser

    class P_(html.parser.HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out, self.role, self.href, self.txt, self.stack, self.buf = [], None, None, [], [], []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', 'th', 'dt', 'p', 'div', 'li', 'td'):
                self.flush_text()
            if tag == 'a' and a.get('href'):
                self.flush_text()
                self.href, self.txt = a['href'], []
            self.stack.append(tag)

        def handle_data(self, d):
            if self.href is not None:
                self.txt.append(d)
            self.buf.append(d)

        def flush_text(self):
            t = ' '.join(''.join(self.buf).split())
            self.buf = []
            if 1 < len(t) < 30 and ROLE_VOCAB.search(t) and not NAME_CJK.match(t) and not re.search(r'主页|信息|访问|院校|学历|[：:]\S|导师简介', t):
                self.role = t

        def handle_endtag(self, tag):
            if tag == 'a' and self.href is not None:
                self.out.append((' '.join(''.join(self.txt).split()), self.href, self.role))
                self.href = None
                self.buf = []
            if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'th', 'dt', 'p', 'li', 'td', 'div'):
                self.flush_text()
            if self.stack:
                self.stack.pop()

    p = P_()
    try:
        p.feed(decode(raw))
    except Exception:
        return []
    return p.out


def is_person_text(t):
    t = t.strip()
    if t in NOT_NAME:
        return False
    return bool(NAME_CJK.match(norm_name(t)) or NAME_LAT.match(t))


def build(school, do_live=True, workers=6):
    rows_in, fc = inputs(school)
    live = Live(school)
    fet = Fetcher(school, live)
    out = []
    pi_sites = {}        # pi -> list of (url, rec) home/profile pages used to look for lab/people links
    todo_fetch = []      # (url) of PI profile/home pages not stored

    # pass 1: profile + home from staged data
    for r in rows_in:
        pi = r['PI']
        c = (fc.get(norm_name(pi)) or [None])[0]
        prof = c['official_profile_url'] if c else None
        if prof:
            u, rec = live.find(prof)
            if rec is None and do_live:
                todo_fetch.append(prof)
        if r['website']:
            u, rec = live.find(r['website'])
            if rec is None and do_live:
                todo_fetch.append(r['website'])
    if do_live and todo_fetch:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(fet.get, list(dict.fromkeys(todo_fetch))))

    # pass 2: link discovery from profile/home pages, fetch candidate people pages and group sites
    pending = {}
    profile_set = {norm_url(x['official_profile_url']) for v in fc.values() for x in v if x.get('official_profile_url')}
    for r in rows_in:
        pi = r['PI']
        c = (fc.get(norm_name(pi)) or [None])[0]
        pages = []
        for u0 in (c and c['official_profile_url'], r['website']):
            if u0:
                u, rec = live.find(u0)
                if rec and rec.get('raw') and not any(norm_url(u) == norm_url(x[0]) for x in pages):
                    pages.append((u0, rec))
        pi_sites[pi] = pages
        for u0, rec in pages:
            host = urllib.parse.urlsplit(u0).hostname
            for href, text in anchors(rec['raw'], rec.get('final_url') or u0):
                if SKIP_HREF.search(href) or urllib.parse.urlsplit(href).scheme not in ('http', 'https'):
                    continue
                h = urllib.parse.urlsplit(href).hostname or ''
                if h == host and PEOPLE.search(text) and len(text) < 20:
                    pending.setdefault(pi, []).append(('people', href, text, u0, rec))
                elif h != host and not W.NOT_A_SITE.search(h) and not W.NOT_FETCHABLE.search(h) and link_kind(text, href, host) and norm_url(href) not in profile_set:
                    pending.setdefault(pi, []).append((link_kind(text, href, host), href, text, u0, rec))
    freq = Counter()
    for pi, lst in pending.items():
        for k in {norm_url(x[1]) for x in lst}:
            freq[k] += 1
    shared_host = Counter(urllib.parse.urlsplit(r['website'] or '').hostname for r in rows_in)

    def first_seg(u):
        return (urllib.parse.urlsplit(u).path.strip('/').split('/') or [''])[0]
    for pi in list(pending):
        keep = []
        for x in pending[pi]:
            kind, href, text, u0, rec0 = x
            if freq[norm_url(href)] >= 3:
                continue        # the same link on 3+ PIs' pages is department / site navigation, not this PI's lab
            if kind == 'people' and shared_host[urllib.parse.urlsplit(href).hostname] >= 3 and first_seg(href) != first_seg(u0):
                continue        # on a shared faculty-space host only the PI's own sub-site counts
            keep.append(x)
        pending[pi] = keep
    fetch_list = []
    for pi, lst in pending.items():
        seen = 0
        for kind, href, text, u0, rec in lst:
            if kind in ('people', 'group', 'pi_home') and seen < 6:
                fetch_list.append(href)
                seen += 1
    if do_live and fetch_list:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(fet.get, list(dict.fromkeys(fetch_list))))
        # depth 2: from fetched external group sites, their people pages
        second = []
        for pi, lst in pending.items():
            for kind, href, text, u0, rec in lst:
                if kind in ('group', 'pi_home'):
                    u, r2 = live.find(href)
                    if r2 and r2.get('raw'):
                        h0 = urllib.parse.urlsplit(href).hostname
                        n = 0
                        for h2, t2 in anchors(r2['raw'], r2.get('final_url') or href):
                            if (urllib.parse.urlsplit(h2).hostname == h0 and PEOPLE.search(t2) and len(t2) < 20
                                    and not SKIP_HREF.search(h2) and n < 3):
                                second.append(h2)
                                pending[pi].append(('people', h2, t2, href, r2))
                                n += 1
        if second:
            with ThreadPoolExecutor(workers) as ex:
                list(ex.map(fet.get, list(dict.fromkeys(second))))

    link_index = {}
    for u, v in list(live.pages.items()):
        if v.get('raw') and v['source'] == 'staged':
            for h, t in anchors(v['raw'], u):
                link_index.setdefault(norm_url(h), (u, v['sha256'], t))
    # rows
    for r in rows_in:
        pi = r['PI']
        c = (fc.get(norm_name(pi)) or [None])[0]
        prof = c['official_profile_url'] if c else None
        site = r['website'] or None
        names = dict(name_zh=pi.strip()) if re.search(r'[一-鿿]', pi) else dict(name_en=pi.strip())
        base = dict(person=pi, role='pi', lab=pi, **names)
        for u0_, rec0_ in pi_sites.get(pi, []):
            m_ = re.findall(r"[A-Z][a-z]+(?: [A-Z][a-z]+){1,2}|[A-Z][A-Za-z]+ [A-Z]{2,}", page_title(rec0_['raw']))
            if m_ and 'name_en' not in base:
                base['name_en_from_page_title'] = m_[0]
        if prof:
            u, rec = live.find(prof)
            ff = dict(kind='official_page', url=c['source_url'], sha256=c['source_sha256'], anchor=c.get('evidence_quote'))
            out.append(base | dict(kind='pi_profile', url=prof, found_from=ff) | fetched_fields(prof, rec))
        elif site and norm_url(site) in link_index:
            u, rec = live.find(site)
            lu, lsha, lt = link_index[norm_url(site)]
            out.append(base | dict(kind='pi_profile', url=site, found_from=dict(kind='official_page', url=lu, sha256=lsha, anchor=lt),
                                   note='university faculty-space page, linked from the official directory') | fetched_fields(site, rec))
            prof = site
        else:
            out.append(base | dict(kind='pi_profile', url=None,
                                   reason='no official faculty-directory profile URL for this PI among the staged faculty candidates '
                                          '(directory entry has no link in the stored copy)'))
        same = bool(site and prof and norm_url(site) == norm_url(prof))
        if site and not same:
            u, rec = live.find(site)
            ff = None
            # who links the site: the profile page, else the directory listing, else the staged discovery
            for src_url in filter(None, [prof]):
                pu, prec = live.find(src_url)
                if prec and prec.get('raw') and any(norm_url(h) == norm_url(site) for h, _ in anchors(prec['raw'], prec.get('final_url') or src_url)):
                    ff = dict(kind='official_page', url=src_url, sha256=prec['sha256'])
            if ff is None and c:
                lu, lrec = live.find(c['source_url'])
                if lrec and lrec.get('raw') and any(norm_url(h) == norm_url(site) for h, _ in anchors(lrec['raw'], c['source_url'])):
                    ff = dict(kind='official_page', url=c['source_url'], sha256=lrec['sha256'])
            if ff is None and norm_url(site) in link_index:
                lu, lsha, lt = link_index[norm_url(site)]
                ff = dict(kind='official_page', url=lu, sha256=lsha, anchor=lt)
            if ff is None:
                same_platform = prof and urllib.parse.urlsplit(site).hostname == urllib.parse.urlsplit(prof).hostname
                ff = dict(kind='discovery', url=prof or site, sha256=(live.find(prof)[1] or {}).get('sha256') if prof else None,
                          note='staged PI website (progress-pi-detail, website_review=%s); the profile page does not link it by '
                               'anchor in the stored copy%s' % (r['website_review'], '; same official platform host as the profile' if same_platform else ''))
            row = base | dict(kind='pi_home', url=site, found_from=ff) | fetched_fields(site, rec)
            row['website_review'] = r['website_review']
            out.append(row)
        elif same:
            u, rec = live.find(site)
            out.append(base | dict(kind='pi_home', url=None,
                                   reason='the university faculty-space page is the only personal page (url equals the pi_profile row); '
                                          'no separate personal site linked from it or the directory'))
        else:
            out.append(base | dict(kind='pi_home', url=None,
                                   reason='no personal website found: faculty profile and directory entry carry no external link '
                                          '(website_review=%s); no page found that links one' % r['website_review']))
        # group / lab sites and member pages
        groups, people_pages, others = {}, [], {}
        for kind, href, text, u0, rec0 in pending.get(pi, []):
            if kind == 'people':
                u, rec = live.find(href)
                people_pages.append((href, text, u0, rec0, rec))
            elif kind in ('group', 'pi_home') and norm_url(href) not in {norm_url(site or ''), norm_url(prof or '')}:
                groups.setdefault(norm_url(href), (kind, href, text, u0, rec0))
        own_home_hosts = {urllib.parse.urlsplit(x).hostname for x in (site,) if x}
        nav_texts = set()
        for u0_, rec0_ in pi_sites.get(pi, []):
            nav_texts |= {t for _h, t in anchors(rec0_['raw'], u0_)}
        kept_hosts = set(own_home_hosts)
        if prof and site and urllib.parse.urlsplit(prof).hostname == urllib.parse.urlsplit(site).hostname:
            kept_hosts.add(urllib.parse.urlsplit(prof).hostname)
        for k, (kind, href, text, u0, rec0) in groups.items():
            u, rec = live.find(href)
            ff = dict(kind='official_page', url=u0, sha256=rec0.get('sha256'), anchor=text)
            from_own_home = bool(site) and norm_url(u0) == norm_url(site)
            names_pi = bool(rec and rec.get('raw') and norm_name(pi) in norm_name(decode(rec['raw'])))
            if rec and rec.get('raw') and not names_pi and not from_own_home:
                out.append(base | dict(kind='pi_other', url=href, found_from=ff, link_type='external organisation or centre link; the page does not name the PI',
                                       **fetched_fields(href, rec)))
                continue
            if names_pi:
                kept_hosts.add(urllib.parse.urlsplit(href).hostname)
            out.append(base | dict(kind='group' if kind == 'group' else 'pi_home', url=href, found_from=ff) | fetched_fields(href, rec))
        people_pages = [x for x in people_pages if urllib.parse.urlsplit(x[0]).hostname in kept_hosts]
        # other (non-fetchable) outbound personal links on the profile / home pages
        for u0, rec0 in pi_sites.get(pi, []):
            for href, text in anchors(rec0['raw'], rec0.get('final_url') or u0):
                h = urllib.parse.urlsplit(href).hostname or ''
                hc = host_class(href)
                if hc and not PROFILE_LINK.search(href):
                    continue
                if hc and urllib.parse.urlsplit(href).scheme in ('http', 'https') and not any(o['url'] == href for o in out if o['person'] == pi):
                    out.append(base | dict(kind='pi_other', url=href, found_from=ff_page(u0, rec0, text), fetched=False, fetch_reason=hc))
        has_lab = [o for o in out if o['person'] == pi and o['kind'] == 'group']
        if has_lab:
            out.append(base | dict(kind='lab', url=has_lab[0]['url'], found_from=has_lab[0]['found_from'], fetched=has_lab[0]['fetched'],
                                   **{k: v for k, v in has_lab[0].items() if k in ('sha256', 'status', 'fetched_at', 'fetch_reason')}))
        else:
            reason = ('the lab is PI-centred; no separate lab website: the PI\'s profile/home page links no lab, group or research-centre site '
                      'by anchor text (checked %d stored page(s))' % len(pi_sites.get(pi, [])))
            if not pi_sites.get(pi):
                reason = 'the lab is PI-centred; no profile or home page of this PI could be read (%s)' % (
                    'no profile URL' if not prof else 'profile not fetched')
            out.append(base | dict(kind='lab', url=None, reason=reason))
        # members from the lab's own people pages
        seen_m = set()
        for href, text, u0, rec0, rec in people_pages:
            if not rec or not rec.get('raw'):
                continue
            pbase = rec.get('final_url') or href
            page_items = role_of_headings(rec['raw'])
            if sum(1 for _t, _h, ro in page_items if ro and '导师' in ro) >= 3:
                continue        # a supervisor directory, not a lab-member list
            for t, h, role in page_items:
                if t in nav_texts or LATIN_NAV.search(t):
                    continue
                try:
                    full = urllib.parse.urljoin(pbase, h)
                except ValueError:
                    continue
                pr = urllib.parse.urlsplit(full)
                if pr.scheme not in ('http', 'https') or SKIP_HREF.search(h) or not is_person_text(t):
                    continue
                if norm_url(full) in {norm_url(pbase), norm_url(site or ''), norm_url(prof or '')} or (t, full) in seen_m:
                    continue
                if W.NOT_A_SITE.search(pr.hostname or '') or 'weixin' in (pr.hostname or '') or pr.hostname == 'githubstatus.com':
                    continue
                seen_m.add((t, full))
                uu, mrec = live.find(full)
                row = dict(person=t.strip(), role='member', lab=pi, kind='member_home', url=full,
                           found_from=dict(kind='lab_page', url=href, sha256=rec['sha256'], anchor=t, section=role),
                           member_role_stated=role if role and '导师' not in role else 'not stated on the page')
                row.update(fetched_fields(full, mrec) if mrec else dict(fetched=False, fetch_reason=host_class(full) or 'queued: member page not fetched in this pass'))
                out.append(row)
    return out, live


def gate(rows):
    bad = []
    for r in rows:
        if r['url']:
            ff = r.get('found_from') or {}
            if not ff.get('url') or not (ff.get('sha256') or ff.get('kind') == 'discovery'):
                bad.append(f"{r['person']} {r['kind']} {r['url']}: found_from url/sha256 missing")
            if not r['fetched'] and not r.get('fetch_reason'):
                bad.append(f"{r['person']} {r['url']}: unfetched without a reason")
        elif not r.get('reason'):
            bad.append(f"{r['person']} {r['kind']}: no URL and no reason")
    return bad


def counts(rows):
    pis = {r['person'] for r in rows if r['role'] == 'pi'}
    c = dict(pis=len(pis))
    for k in ('pi_profile', 'pi_home', 'lab', 'group', 'pi_other', 'member_home'):
        sel = [r for r in rows if r['kind'] == k]
        c[k] = dict(url=sum(1 for r in sel if r['url']), reason=sum(1 for r in sel if not r['url']),
                    fetched=sum(1 for r in sel if r['url'] and r['fetched']),
                    unfetchable=sum(1 for r in sel if r['url'] and not r['fetched']))
    c['labs_neither'] = sum(1 for p in pis if not any(r['person'] == p and r['kind'] == 'lab' and (r['url'] or r.get('reason')) for r in rows))
    c['unreachable'] = sum(1 for r in rows if r['url'] and 'unreachable' in r.get('fetch_reason', ''))
    c['wayback_queue'] = sorted({r['url'] for r in rows if r['url'] and 'Wayback' in r.get('fetch_reason', '') and 'queued: not fetched' not in r.get('fetch_reason', '')})
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['build', 'offline', 'summary', 'sample'])
    ap.add_argument('school', choices=SCHOOLS)
    ap.add_argument('--seed', type=int, default=20261108)
    ap.add_argument('--n', type=int, default=30)
    ap.add_argument('--out')
    a = ap.parse_args()
    out = Path(a.out) if a.out else P.data_w('person-websites.json', a.school)
    if a.cmd in ('build', 'offline'):
        rows, live = build(a.school, do_live=(a.cmd == 'build'))
        doc = dict(school=a.school, tool='tools/person_websites_cn.py', review_status='automatic',
                   source='progress-pi-detail.csv, faculty-candidates.json, staged live captures, own live pass %s' % NOW, rows=rows)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    else:
        rows = json.load(open(out))['rows']
    bad = gate(rows)
    if a.cmd == 'sample':
        pool = [r for r in rows if r['url']]
        for r in random.Random(a.seed).sample(pool, min(a.n, len(pool))):
            print(json.dumps(r, ensure_ascii=False))
        return 0
    c = counts(rows)
    print(a.school, json.dumps(c, ensure_ascii=False), 'gate_problems', len(bad))
    for b in bad[:5]:
        print('  !', b, file=sys.stderr)
    return int(bool(bad))


if __name__ == '__main__':
    sys.exit(main())
