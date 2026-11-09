"""Personal websites of a school's PIs and students (owner request 2026-11-08: every website we can get).

A URL counts only when an official page, or the person's own verified page, links it: the department directory, a faculty
profile, a lab people page, a thesis/listing page. Nothing is guessed from a name pattern. Every row keeps the URL, the
page that links it (url + sha256 + anchor text), whether we fetched it (date, HTTP status, sha256), and its kind
(lab | pi_home | pi_profile | group | student_home). Hosts we never fetch (Google Scholar, LinkedIn, X, GitHub, ...) are
recorded with fetched=false and the reason. A person with no URL gets a specific reason.

  person_sweep.py harvest <school>    offline: links next to a person's name on the school's stored official pages
                                          -> <scratch>/person-sweep/<school>/candidates.json
  person_sweep.py fetch <school> [--shard i/n] [--limit N]
                                          live, robots-checked, >= 3 s per host; -> <scratch>/person-sweep/<school>/fetch.<i>.jsonl
  person_sweep.py build <school> [--out PATH]
                                          assemble hierarchy/<school>/reviewed/person-sweep.json (+ the PI side)
  person_sweep.py summary <school>     counts for the report
  person_sweep.py sample <school> [--n 30] [--seed S]   the hand-check sample (printed as JSON)

Websites only: this module never changes a student or membership relation.
"""
import argparse
import collections
import hashlib
import json
import os
import random
import re
import sqlite3
import time
import unicodedata
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P  # noqa: E402

SCRATCH = Path(os.environ.get('PERSON_WEBSITES_OUT') or P.SCRATCH / 'person-sweep')
UA = 'Mozilla/5.0 (compatible; research-atlas-reader)'
TODAY = time.strftime('%Y-%m-%d', time.gmtime())

WAYBACK = re.compile(r'^https?://web\.archive\.org/web/\d+(?:id_|if_|im_)?/(https?://.+)$')
# Hosts we record but never fetch: login walls and bot-hostile profile hosts (brief: Scholar, LinkedIn, X).
NO_FETCH = re.compile(r'(^|\.)(linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|scholar\.google\.[a-z.]+|github\.com|'
                      r'bsky\.app|threads\.net|mastodon\.[a-z.]+|medium\.com|youtube\.com|youtu\.be|researchgate\.net|academia\.edu|'
                      r'orcid\.org|semanticscholar\.org|kaggle\.com|huggingface\.co|stackoverflow\.com|notion\.site)$', re.I)
# Not a person's website at all: paper hosts, indexes, banned sources.
DROP_HOSTS = re.compile(r'(^|\.)(dblp\d*\.org|dblp\d*\.uni-trier\.de|arxiv\.org|doi\.org|dl\.acm\.org|acm\.org|ieeexplore\.ieee\.org|ieee\.org|'
                        r'openreview\.net|openalex\.org|wikipedia\.org|wikidata\.org|mathgenealogy\.org|genealogy\.math\.ndsu\.nodak\.edu|'
                        r'academictree\.org|deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu|zbmath\.org|scopus\.com|'
                        r'springer\.com|sciencedirect\.com|jstor\.org|aclanthology\.org|proceedings\.mlr\.press|neurips\.cc|nips\.cc|'
                        r'semanticscholar\.org|pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov|zoom\.us|calendly\.com|google\.com|goo\.gl|'
                        r'bit\.ly|forms\.gle|docs\.google\.com|drive\.google\.com|dropbox\.com|overleaf\.com|mailto)$', re.I)
OUTPUT_PATH = re.compile(r'/(?:publications?|papers?|reports?|abs|pdf)/|\.(?:pdf|ps|docx?|pptx?|zip|png|jpe?g|gif|mp4)$', re.I)
GENERIC_TEXT = re.compile(r'^\W*(?:personal\s+)?(?:web\s*site|website|web\s*page|webpage|home\s*page|homepage|personal\s+(?:page|site)|'
                          r'www|my\s+(?:page|site|website|homepage)|\[?\s*(?:www|web)\s*\]?)\W*$', re.I)
SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv'}
TOKEN = re.compile(r"[^\W_]+", re.U)
JUNK_PAGE_ROLES = re.compile(r'/(?:calendar|events?|news)/', re.I)


def fold(s):
    s = unicodedata.normalize('NFKD', (s or '').replace('’', "'").replace('‘', "'"))
    return ''.join(c for c in s if not unicodedata.combining(c)).casefold()


def toks(s):
    return [t for t in TOKEN.findall(fold(s).replace("'", '')) if t not in SUFFIX]


def name_keys(name, reverse=False):
    """Full-name keys for one written form: 'First M. Last', 'Last, First', and the first+last pair without middles."""
    name = re.sub(r'\([^)]*\)', ' ', name or '')
    if name.count(',') == 1:
        a, b = name.split(',')
        name = f'{b} {a}'
    t = toks(name)
    if len(t) < 2:
        return set()
    keys = {' '.join(t), f'{t[0]} {t[-1]}' if len(t) > 2 else ' '.join(t)}
    keys = {k for k in keys if len(k) > 5}
    if reverse and len(t) == 2:
        keys.add(f'{t[1]} {t[0]}')
    return keys


def orig_url(url):
    m = WAYBACK.match(url or '')
    return m.group(1) if m else url


def norm_url(url):
    sp = urlsplit(orig_url(url) or '')
    host = (sp.hostname or '').lower()
    host = re.sub(r'^www\.', '', host)
    return f'{host}{sp.path.rstrip("/")}' + (f'?{sp.query}' if sp.query else '')


def sha_of(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- inputs
def rd(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def load_people(school):
    pis = json.loads(P.data('pis.json', school).read_text())
    students = json.loads(P.data('students.json', school).read_text())
    persons = {}   # id -> dict(name, names, pis, sources:set(norm url))
    for pi, rows in students.items():
        for r in rows:
            p = persons.setdefault(r['person'], dict(id=r['person'], name=r['name'], names={r['name'], *(r.get('aliases') or [])},
                                                     pis=set(), roles=set(), sources=set()))
            p['pis'].add(pi)
            p['roles'].update(r.get('roles') or [])
            for rel in r.get('relations') or []:
                for s in rel.get('sources') or []:
                    if s.get('url'):
                        p['sources'].add(norm_url(s['url']))
    return pis, students, persons


def lab_pages(school):
    """pi -> normalized urls of the lab pages the audit read (people pages, students pages)."""
    import gzip
    out = collections.defaultdict(set)
    path = P.data('labpage-audit.jsonl.gz', school)
    if not path.exists():
        return out
    with gzip.open(path, 'rt') as f:
        for line in f:
            r = json.loads(line)
            lp = r.get('lab_page') or {}
            for u in (lp.get('urls') or {}).values():
                if u:
                    out[r['pi']].add(norm_url(u))
            for u in (r.get('students') or {}).get('pages') or []:
                out[r['pi']].add(norm_url(u))
            for c in lp.get('checks') or []:
                if c.get('kind') in ('people', 'seed', 'site') and c.get('url'):
                    out[r['pi']].add(norm_url(c['url']))
    return out


STORE_NAMES = ['labpage-audit-captures.sqlite', 'labpage-captures.sqlite', 'gap-captures.sqlite', 'few-students-captures.sqlite',
               'thesis-captures.sqlite', 'school-captures.sqlite']


def iter_pages(school):
    """(url, capture_url, sha256, fetched_at, bytes) for every status-200 HTML capture of the school's stores."""
    seen = set()
    for name in STORE_NAMES:
        path = P.data(name, school)
        if not path.exists():
            continue
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        if 'captures' in tables:
            cols = {r[1] for r in con.execute('pragma table_info(captures)')}
            if 'content' in cols:
                q = ("select url, capture_url, sha256, fetched_at, content, content_type from captures where status=200 "
                     "and content is not null and error is null")
                for url, cap, sha, at, content, ct in con.execute(q):
                    if (url, cap, sha) in seen or (ct and 'html' not in ct.lower() and 'xml' not in ct.lower()):
                        continue
                    seen.add((url, cap, sha))
                    yield url, cap, sha, at, content
            elif 'raw_zlib' in cols:
                for url, cap, at, sha, ct, raw in con.execute('select page_url, capture_url, fetched_at, sha256, content_type, raw_zlib '
                                                              'from captures where http_status=200 and raw_zlib is not null'):
                    if (url, cap, sha) in seen or (ct and 'html' not in ct.lower()):
                        continue
                    seen.add((url, cap, sha))
                    yield url, cap, sha, at, raw
        if 'live' in tables:
            for url, at, sha, ct, raw in con.execute('select url, fetched_at, sha256, content_type, raw_zlib from live where status=200 and raw_zlib is not null'):
                if (url, None, sha) in seen or (ct and 'html' not in ct.lower()):
                    continue
                seen.add((url, None, sha))
                yield url, None, sha, at, raw
        con.close()


def html_of(content):
    for _ in range(2):
        try:
            content = zlib.decompress(content)
        except (zlib.error, TypeError):
            break
    if isinstance(content, str):
        content = content.encode()
    if content[:2] == b'\x1f\x8b':
        import gzip
        try:
            content = gzip.decompress(content)
        except OSError:
            pass
    return content


def link_class(url):
    host = (urlsplit(url).hostname or '').lower()
    if NO_FETCH.search(host):
        return 'social_or_profile'
    return 'web'


# ---------------------------------------------------------------- harvest
def harvest(school):
    from lxml import html as LH
    pis, students, persons = load_people(school)
    lp_pages = lab_pages(school)
    pi_names = {}
    for p in pis:
        for n in set(p.get('names') or []) | {p['pi']}:
            for k in name_keys(n):
                pi_names.setdefault(k, set()).add(p['pi'])
    key_people = collections.defaultdict(set)      # key -> person ids
    key_rev = collections.defaultdict(set)         # reversed 2-token keys (strong sources only)
    for pid, p in persons.items():
        for n in p['names']:
            for k in name_keys(n):
                key_people[k].add(pid)
            for k in name_keys(n, reverse=True) - name_keys(n):
                key_rev[k].add(pid)
    domain = (json.loads(P.data('pis.json', school).read_text())[0].get('domain') if False else None)
    cands = {}
    stats = collections.Counter()
    pages = 0
    src_index = collections.defaultdict(set)       # normalized page url -> person ids the page is a source for
    for pid, p in persons.items():
        for u in p['sources']:
            src_index[u].add(pid)
        for pi in p['pis']:
            for u in lp_pages.get(pi, ()):
                src_index[u].add(pid)
    searched = collections.defaultdict(list)       # person id -> [page url, sha] parsed for them
    for url, cap, sha, at, content in iter_pages(school):
        pages += 1
        raw = html_of(content)
        if len(raw) > 6_000_000:
            continue
        base = orig_url(url)
        page_key = norm_url(url)
        for pid in src_index.get(page_key, ()):
            if len(searched[pid]) < 40:
                searched[pid].append([orig_url(url), sha])
        try:
            doc = LH.fromstring(raw, base_url=base)
        except Exception:  # noqa: BLE001
            stats['unparsable'] += 1
            continue
        for a in doc.iter('a'):
            href = (a.get('href') or '').strip()
            if not href or href.startswith(('#', 'mailto:', 'javascript:', 'tel:')):
                continue
            try:
                target = urljoin(base, href)
            except ValueError:
                continue
            target = orig_url(target)
            sp = urlsplit(target)
            if sp.scheme not in ('http', 'https') or not sp.hostname:
                continue
            if norm_url(target) == page_key or DROP_HOSTS.search(sp.hostname) or OUTPUT_PATH.search(sp.path):
                continue
            text = ' '.join(a.text_content().split())
            how = None
            keys = set()
            if text and not GENERIC_TEXT.match(text):
                keys = name_keys(text, reverse=True)
                if keys:
                    how = 'anchor_text_is_name'
            if not keys and text and GENERIC_TEXT.match(text):
                # a 'homepage' / 'website' link (or an image link) inside a one-person card
                node = a
                for _ in range(4):
                    node = node.getparent()
                    if node is None or node.tag in ('body', 'html'):
                        break
                    ctext = ' '.join(node.text_content().split())
                    if len(ctext) > 400 or len(node.findall('.//a')) > 4:
                        break
                    words = toks(ctext)
                    hit = set()
                    for i in range(len(words)):
                        for n in (2, 3, 4):
                            k = ' '.join(words[i:i + n])
                            if k in key_people or k in pi_names:
                                hit.add(k)
                    # one person only: the card may repeat a name, never name two people
                    ids = set()
                    for k in hit:
                        ids |= key_people.get(k, set()) | {('pi', x) for x in pi_names.get(k, set())}
                    if len(ids) == 1 or (hit and len({frozenset(key_people.get(k, set()) | {('pi', x) for x in pi_names.get(k, set())}) for k in hit}) == 1):
                        keys, how = hit, 'homepage_link_in_one_person_card'
                        break
                    if ids:
                        break
            if not keys:
                continue
            ids = set()
            for k in keys:
                ids |= key_people.get(k, set())
            rev = set()
            for k in keys:
                rev |= key_rev.get(k, set())
            who = []
            for pid in sorted(ids | rev):
                p = persons[pid]
                strong = page_key in p['sources'] or any(page_key in lp_pages.get(pi, ()) for pi in p['pis'])
                if strong:
                    who.append((pid, 'page_is_a_recorded_source_of_this_person'))
                elif pid in ids and len(ids) == 1:
                    who.append((pid, 'only_person_in_school_with_this_name'))
            pi_who = sorted({pi for k in keys for pi in pi_names.get(k, ())})
            if not who and not pi_who:
                stats['name_hit_ambiguous_or_unsourced'] += 1
                continue
            for pid, scope in who:
                key = (pid, norm_url(target))
                cur = cands.setdefault(key, dict(person=pid, name=persons[pid]['name'], url=target, found=[]))
                if len(cur['found']) < 4 and not any(f['page_sha256'] == sha for f in cur['found']):
                    cur['found'].append(dict(page_url=orig_url(url), capture_url=cap, page_sha256=sha, page_fetched_at=at,
                                             anchor=text[:120], how=how, scope=scope))
            for pi in pi_who:
                key = (('pi', pi), norm_url(target))
                cur = cands.setdefault(key, dict(person=None, pi=pi, name=pi, url=target, found=[]))
                if len(cur['found']) < 4 and not any(f['page_sha256'] == sha for f in cur['found']):
                    cur['found'].append(dict(page_url=orig_url(url), capture_url=cap, page_sha256=sha, page_fetched_at=at,
                                             anchor=text[:120], how=how, scope='pi_name'))
    out = SCRATCH / school
    out.mkdir(parents=True, exist_ok=True)
    rows = list(cands.values())
    (out / 'candidates.json').write_text(json.dumps(dict(school=school, harvested_at=TODAY, pages=pages, stats=dict(stats), candidates=rows, searched=searched, source_pages={pid: len(p['sources']) for pid, p in persons.items()}),
                                                    ensure_ascii=False, indent=0))
    print(school, 'pages', pages, 'candidates', len(rows), 'persons', len({r['person'] for r in rows if r['person']}), dict(stats))


# ---------------------------------------------------------------- fetch
class Fetcher:
    def __init__(self):
        import own_page_students as O
        self.rb = O.Robots()
        import threading
        self.lock = threading.Lock()
        self.hostlock = collections.defaultdict(threading.Lock)

    def get(self, url):
        import urllib.request as R
        sp = urlsplit(url)
        out = dict(url=url, fetched=False, at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        if NO_FETCH.search(sp.hostname or ''):
            out['reason'] = 'host not fetchable (robots/login): recorded from the official page, never fetched'
            return out
        with self.hostlock[sp.netloc]:
            with self.lock:
                known = sp.netloc in self.rb.cache
            ok, delay = self.rb.allowed(url)
            flag = self.rb.cache.get(sp.netloc, (None, 0, 'ok'))[2]
            if flag == 'ai_group':
                out['reason'] = 'robots.txt names ClaudeBot/anthropic-ai/Claude-Web: host not used in any form'
                return out
            if not ok:
                out['reason'] = 'robots.txt disallows this path' if delay is not None and self.rb.cache[sp.netloc][0] not in (None,) else 'robots.txt not retrievable: not fetched'
                return out
            self.rb.wait(sp.netloc, delay)
            try:
                req = R.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,*/*;q=0.5'})
                with R.urlopen(req, timeout=25) as r:
                    raw = r.read(4_000_000)
                    out.update(status=r.status, final_url=r.geturl(), content_type=r.headers.get('Content-Type', ''))
            except Exception as e:  # noqa: BLE001
                code = getattr(e, 'code', None)
                out['status'] = code
                if code in (401, 403, 429):
                    out['reason'] = f'HTTP {code}: host refuses automated access; queued for Wayback (shared throttle), not retried live'
                    out['wayback_queue'] = True
                elif code in (404, 410):
                    out['reason'] = f'HTTP {code}: page gone'
                else:
                    out['reason'] = f'unreachable ({type(e).__name__})'
                return out
        if re.search(rb'(Just a moment|cf_chl_opt|Attention Required|Verifying you are human|px-captcha|Pardon Our Interruption|not a bot)', raw[:20000], re.I):
            out.update(reason='bot challenge: not read; queued for Wayback', wayback_queue=True)
            return out
        out.update(fetched=True, sha256=sha_of(raw), bytes=len(raw))
        try:
            text = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw.decode('utf8', 'replace'))
            text = re.sub(r'<[^>]+>', ' ', text)
            out['text_head'] = ' '.join(text.split())[:3000]
            m = re.search(r'(?is)<title[^>]*>(.*?)</title>', raw.decode('utf8', 'replace'))
            out['title'] = ' '.join(m.group(1).split())[:200] if m else None
        except Exception:  # noqa: BLE001
            pass
        return out


def fetch(school, shard=(0, 1), limit=None, workers=12, urls=None):
    cands = json.loads((SCRATCH / school / 'candidates.json').read_text())['candidates']
    domain = school_domain(school)
    todo = urls or sorted({c['url'] for c in cands if classify(c['url'], domain) in ('personal_site', 'lab_site')})
    reg = P.data('lab-websites.json', school)
    for p_ in (Path(os.environ['PERSON_WEBSITES_REGISTER']) if os.environ.get('PERSON_WEBSITES_REGISTER') else reg,):
        if p_.exists() and not urls:   # the lab register's pages (a lab or PI home page) are fetched too
            todo = sorted(set(todo) | {r['url'] for r in json.loads(p_.read_text()).get('labs', []) if r.get('url') and r.get('coverage') != 'reason'})
    todo = [u for u in todo if hash(urlsplit(u).netloc) is not None and zlib.crc32((urlsplit(u).hostname or '').encode()) % shard[1] == shard[0]]
    if limit:
        todo = todo[:limit]
    path = SCRATCH / school / f'fetch.{shard[0]}.jsonl'
    done = set()
    if path.exists():
        done = {json.loads(l)['url'] for l in path.open()}
    todo = [u for u in todo if u not in done]
    f = Fetcher()
    # one worker per host at a time (hostlock), many hosts at once
    by_host = collections.defaultdict(list)
    for u in todo:
        by_host[urlsplit(u).netloc].append(u)
    print(school, 'urls to fetch', len(todo), 'hosts', len(by_host), flush=True)
    with path.open('a') as out:
        def run(host):
            return [f.get(u) for u in by_host[host]]
        with ThreadPoolExecutor(workers) as ex:
            for n, res in enumerate(ex.map(run, sorted(by_host))):
                for r in res:
                    out.write(json.dumps(r, ensure_ascii=False) + '\n')
                out.flush()
                if n % 200 == 0:
                    print('hosts done', n, flush=True)



# ---------------------------------------------------------------- build
NEWSY = re.compile(r'/(?:news|events?|article|articles|story|stories|blog|press|calendar|talks?|seminars?|courses?|class(?:es)?)(?:/|$)|/20\d\d/', re.I)
MEMBER_PATH = re.compile(r'/(?:people|members?|team|students?|alumni|person|persons|directory|profiles?|faculty|staff|bios?|grad|researchers|group)/[^/]+/?$', re.I)


def school_domain(school):
    import labpage_audit as L
    return L.SCHOOLS[school]['domain']


def classify(url, domain):
    sp = urlsplit(url)
    host = (sp.hostname or '').lower()
    if NO_FETCH.search(host):
        return 'social_or_profile'
    on_school = bool(re.search(domain, host))
    dom_dots = domain.replace('\\', '').count('.')
    depth = host.count('.') - dom_dots   # labels left of the school domain (www.cs.princeton.edu: 2)
    path = sp.path or '/'
    if on_school and re.search(r'person_id=|/person\.html|username=|/directory/|/user/\d+', url):
        return 'school_profile'
    if on_school:
        if re.match(r'^(?:scholar|profiles?)\.', host) and path.strip('/') and not re.search(r'/(?:people|directory|faculty)/?$', path):
            return 'personal_site' if host.startswith('scholar.') or '.scholar.' in host else 'school_profile'
        if re.search(r'\.scholar\.', host):
            return 'personal_site'
        if '/~' in path or re.search(r'/(?:u|users?)/[^/]+', path):
            return 'personal_site'
        if MEMBER_PATH.search(path) and path.strip('/').count('/') >= 1:
            return 'school_profile' if re.search(r'/(?:people|directory|faculty|profiles?|person|persons|bios?|staff)/', path) and depth <= 2 else 'lab_member_page'
        if path.strip('/') == '' or path.strip('/').count('/') == 0 and depth >= 1:
            return 'lab_site' if depth >= 1 and not host.startswith('www.') else 'school_page'
        return 'school_page'
    if NEWSY.search(path):
        return 'news_or_event'
    return 'personal_site'


def load_fetch(school):
    out = {}
    for f in sorted((SCRATCH / school).glob('fetch.*.jsonl')):
        for line in f.open():
            r = json.loads(line)
            out[r['url']] = r
    return out


def fetched_block(r):
    if not r:
        return dict(fetched=False, reason='not fetched in this pass')
    b = dict(fetched=bool(r.get('fetched')), at=r.get('at'))
    for k in ('status', 'sha256', 'final_url', 'title', 'reason', 'wayback_queue'):
        if r.get(k) not in (None, ''):
            b[k] = r[k]
    return b


def persons_sources(pid, persons):
    return persons[pid]['sources']


def build(school, out=None):
    data = json.loads((SCRATCH / school / 'candidates.json').read_text())
    fetched = load_fetch(school)
    domain = school_domain(school)
    pis, students, persons = load_people(school)
    reg_path = Path(out).parent / 'lab-websites.json' if out else P.data('lab-websites.json', school)
    register = json.loads(reg_path.read_text()) if reg_path.exists() else {'labs': []}
    rows, by_person = [], collections.defaultdict(list)
    pi_rows = collections.defaultdict(list)
    for c in data['candidates']:
        if DROP_HOSTS.search(urlsplit(c['url']).hostname or ''):
            continue
        st = classify(c['url'], domain)
        if st in ('personal_site', 'lab_site') and not c.get('person') is None:
            host, path = urlsplit(c['url']).hostname, urlsplit(c['url']).path
            if host == urlsplit(c['found'][0]['page_url']).hostname and '/~' not in path and (MEMBER_PATH.search(path) or re.search(r'/author/', path)):
                st = 'lab_member_page'   # the lab's own people page for this student, not a personal site
        if st in ('news_or_event', 'school_page'):
            continue
        pi_scope = c.get('person') is None
        if pi_scope and not any(f['how'] == 'anchor_text_is_name' for f in c['found']) and st not in ('personal_site', 'lab_site'):
            continue
        row = dict(school=school, role='pi' if pi_scope else 'student', person=c.get('person'), name=c['name'], pi=c.get('pi') or sorted(persons[c['person']]['pis']),
                   url=c['url'], site_type=st, found_from=c['found'], fetched=fetched_block(fetched.get(c['url'])))
        if st == 'social_or_profile':
            row['fetched'] = dict(fetched=False, at=TODAY, reason='host not fetchable (robots/login): recorded from the official page, never fetched')
        if pi_scope:
            row['kind'] = {'school_profile': 'pi_profile', 'lab_site': 'group', 'lab_member_page': 'pi_profile'}.get(st, 'pi_home')
            pi_rows[c['pi']].append(row)
        else:
            row['kind'] = 'student_home'
            row['counts_as_home_page'] = st in ('personal_site', 'lab_site') and any(f['scope'] == 'page_is_a_recorded_source_of_this_person' for f in c['found'])   # a name-only match elsewhere in the school is not enough (a template-designer credit matched a student)
            by_person[c['person']].append(row)
        rows.append(row)
    searched = data.get('searched') or {}
    no_url = []
    for pid, p in sorted(persons.items()):
        have = [r for r in by_person.get(pid, ()) if r['counts_as_home_page']]
        if have:
            continue
        s = searched.get(pid) or []
        total = data['source_pages'].get(pid, 0)
        others = [r for r in by_person.get(pid, ())]
        if s:
            reason = (f"no personal-site link beside this person's name on the {len(s)} stored official page(s) that list them"
                      f" ({'; '.join(sorted({u for u, _ in s})[:2])}); no own page linked from any of them")
            if others:
                reason += f"; only profile, lab-member or name-only (unverified) links were found ({sorted({r['site_type'] for r in others})})"
        else:
            hosts = sorted({u.split('/')[0] for u in persons_sources(pid, persons)})
            if hosts and all(re.search(r'dspace|figshare|arks\.|dataspace|repository|infoscience|escholarship|ethz|thesis', h) for h in hosts):
                reason = (f"listed only by thesis-repository record(s) on {', '.join(hosts)}: such a record names the thesis, not a personal site, and the repository "
                          "is not crawled for links; no stored official page lists this person with a link; no own page linked from any official page")
            else:
                reason = f"none of this person's {total} source page(s) is in the capture stores, so no official page was searched for a link: gap, needs a fetch"
        no_url.append(dict(school=school, person=pid, name=p['name'], role='student', pi=sorted(p['pis']), searched_pages=len(s),
                           source_pages=total, reason=reason, reason_kind='searched_no_link' if s else ('thesis_record_only' if reason.startswith('listed only by thesis') else 'source_pages_not_stored')))
    doc = dict(school=school, tool='tools/person_sweep.py', built_at=TODAY, review_status='generated; websites only, no relation changes',
               rows=rows, students_without_website=no_url, pis=pi_side(school, register, pi_rows, fetched, pis),
               counts=summary_of(school, rows, no_url, persons, register, pis))
    return doc


def summary_of(school, rows, no_url, persons, register, pis):
    st = collections.Counter()
    homes = {r['person'] for r in rows if r['role'] == 'student' and r.get('counts_as_home_page')}
    fetched_rows = [r for r in rows if r['role'] == 'student' and r.get('counts_as_home_page')]
    out = dict(students=len(persons), students_with_home_page=len(homes), students_with_reason=len(no_url),
               students_neither=len(persons) - len(homes) - len(no_url),
               student_home_urls=len({r['url'] for r in fetched_rows}),
               student_urls_fetched=len({r['url'] for r in fetched_rows if r['fetched'].get('fetched')}),
               recorded_not_fetchable=len({r['url'] for r in rows if r['site_type'] == 'social_or_profile'}),
               reasons_source_pages_not_stored=sum(1 for r in no_url if r['reason_kind'] == 'source_pages_not_stored'))
    for r in rows:
        st[r['role'] + ':' + r['site_type']] += 1
    out['row_types'] = dict(st)
    return out


def pi_counts(pi_recs):
    c = collections.Counter()
    for r in pi_recs:
        kinds = {u['kind'] for u in r['urls']}
        c['pis'] += 1
        c['with_lab_or_home'] += bool({'lab', 'pi_home', 'group'} & kinds)
        c['with_home_page'] += 'pi_home' in kinds
        c['with_profile'] += 'pi_profile' in kinds
        c['with_reason_only'] += (not ({'lab', 'pi_home', 'group'} & kinds)) and bool(r['reasons'])
        c['neither'] += (not ({'lab', 'pi_home', 'group'} & kinds)) and not r['reasons']
    return dict(c)



def audit_pi_checks(school):
    import gzip
    out = {}
    path = P.data('labpage-audit.jsonl.gz', school)
    with gzip.open(path, 'rt') as f:
        for line in f:
            r = json.loads(line)
            out[r['pi']] = (r.get('lab_page') or {}).get('checks') or []
    return out


def pi_side(school, register, pi_rows, fetched, pis):
    """One record per PI: lab/home page (from the lab register), official profile (from the audit's school_profile check), extra links."""
    checks = audit_pi_checks(school)
    labs = {r['pi']: r for r in register.get('labs', [])}
    out = []
    for p in pis:
        pi = p['pi']
        lab = labs.get(pi) or {}
        rec = dict(pi=pi, person_ids=p.get('personIds'), urls=[], reasons=[])
        gaps = set(lab.get('evidence_gaps') or [])
        if lab.get('url') and 'selected_url_is_profile_card' in gaps:
            rec['urls'].append(dict(kind='pi_profile', url=lab['url'], site_type='school_profile', found_from=dict(url=None, via=lab.get('found_via'), note='selected by the lab-page audit; an institutional profile card, not a home page'),
                                    fetched=fetched_block(fetched.get(lab['url']))))
        elif lab.get('url') and 'selected_url_is_research_output' not in gaps and lab.get('coverage') in ('website', 'pending') and lab.get('kind') != 'other_institution_site':
            ev = (lab.get('official_link_evidence') or [{}])[0]
            ff = dict(url=ev.get('on') or lab.get('listed_on'), anchor=ev.get('anchor'), sha256=ev.get('source_sha256') or (ev.get('provenance_chain') or [{}])[0].get('source_sha256'),
                      via=ev.get('source') or lab.get('found_via')) if ev or lab.get('listed_on') else dict(url=None, via=lab.get('found_via'), note='discovered by the lab-page audit; no official page link recorded yet')
            rec['urls'].append(dict(kind='lab' if lab.get('kind') == 'lab_site' else 'pi_home', url=lab['url'], site_type='register', found_from=ff,
                                    fetched=fetched_block(fetched.get(lab['url'])) | ({'sha256_store_capture': lab.get('sha256')} if lab.get('sha256') else {})))
        prof = [c for c in checks.get(pi, []) if c.get('source') == 'school_profile' and c.get('result') in ('ok', 'ok_wayback') and c.get('url')]
        listing = next((c for c in checks.get(pi, []) if c.get('source') == 'department_listing' and c.get('result') in ('ok', 'ok_wayback')), None)
        if prof:
            c = prof[0]
            rec['urls'].append(dict(kind='pi_profile', url=c['url'], site_type='school_profile',
                                    found_from=dict(url=listing['url'], sha256=listing.get('sha256'), via='department_listing') if listing else dict(url=None, note='profile URL from the audit school_profile check'),
                                    fetched=dict(fetched=True, at=c.get('at'), status=200, sha256=c.get('sha256'), reason='captured by the lab-page audit')))
        seen = {norm_url(u['url']) for u in rec['urls']}
        for r in pi_rows.get(pi, ()):
            if norm_url(r['url']) in seen or r['site_type'] in ('lab_member_page',):
                continue
            seen.add(norm_url(r['url']))
            if r['kind'] == 'pi_profile' and any(u['kind'] == 'pi_profile' for u in rec['urls']):
                continue
            rec['urls'].append(dict(kind=r['kind'], url=r['url'], site_type=r['site_type'], found_from=r['found_from'][0], fetched=r['fetched']))
        kinds = {u['kind'] for u in rec['urls']}
        if not ({'lab', 'pi_home', 'group'} & kinds):
            rec['reasons'].append(dict(kind='no_lab_or_home_page', reason=lab.get('reason') or 'no lab or home page recorded: no entry in the lab register'))
        if 'pi_profile' not in kinds:
            rec['reasons'].append(dict(kind='no_profile', reason='no official faculty profile page captured: the department listing has no profile link for this PI'))
        out.append(rec)
    return out


def apply_register(school, register_path, fetched, cand_doc):
    """Close 'page_capture_hash_missing' with the live fetch, and record official links harvested from stored official pages."""
    import lab_websites as LW
    reg = json.loads(Path(register_path).read_text())
    domain = school_domain(school)
    by_url = collections.defaultdict(list)
    for c in cand_doc['candidates']:
        if c.get('person') is None:
            by_url[norm_url(c['url'])].append(c)
    changed = 0
    for r in reg['labs']:
        if not r.get('url'):
            continue
        f = fetched.get(r['url'])
        if 'page_capture_hash_missing' in r.get('evidence_gaps', []) and f and f.get('fetched') and f.get('sha256'):
            r['sha256'] = f['sha256']
            r['checks'].append(dict(source='live_fetch_websites_1108', url=r['url'], at=f['at'], result='ok', sha256=f['sha256'], status=f.get('status'),
                                    final_url=f.get('final_url'), via=r.get('found_via')))
            r['evidence_gaps'] = [g for g in r['evidence_gaps'] if g != 'page_capture_hash_missing']
            changed += 1
        if r.get('official_link_status') != 'recorded':
            for c in by_url.get(norm_url(r['url']), ()):
                if c['pi'] != r['pi']:
                    continue
                for ff in c['found']:
                    host = urlsplit(ff['page_url']).hostname or ''
                    if re.search(domain, host) and ff['how'] == 'anchor_text_is_name' and norm_url(ff['page_url']) != norm_url(r['url']):
                        chk = dict(source='department_listing_link', url=r['url'], on=ff['page_url'], at=ff['page_fetched_at'], result='listed', anchor=ff['anchor'],
                                   linked_url=c['url'], source_sha256=ff['page_sha256'], provenance='recovered_from_stored_official_page_by_person_sweep')
                        r['checks'].append(chk)
                        r['official_link_status'], r['official_link_evidence'], r['listed_on'] = 'recorded', [chk], ff['page_url']
                        changed += 1
                        break
                if r.get('official_link_status') == 'recorded':
                    break
        if not r['evidence_gaps'] and r.get('coverage') == 'pending' and r.get('kind') in ('lab_site', 'pi_homepage') and r.get('sha256'):
            r['coverage'] = 'website'
            r['reason'] = 'Captured lab/group website.' if r.get('kind') == 'lab_site' else 'Captured PI homepage used as the lab-page fallback.'
    Path(register_path).write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
    return changed, LW.counts(reg)


def sample(school, n=30, seed=20261108, path=None):
    """The hand-check sample: n recorded student/PI URLs that were fetched, with the evidence a reader needs (name on page, affiliation words)."""
    doc = json.loads(Path(path or P.data('person-sweep.json', school)).read_text())
    pool = [r for r in doc['rows'] if r['fetched'].get('fetched') and r['site_type'] in ('personal_site', 'lab_site') and r['role'] == 'student']
    rng = random.Random(seed)
    out = []
    for r in rng.sample(pool, min(n, len(pool))):
        fetched = load_fetch(school).get(r['url'], {})
        text = fold(fetched.get('text_head') or '')
        t = toks(r['name'])
        out.append(dict(name=r['name'], url=r['url'], title=fetched.get('title'), family_on_page=bool(t) and t[-1] in text,
                        given_on_page=bool(t) and t[0] in text, school_word=bool(re.search(school, text)), found_on=r['found_from'][0]['page_url'],
                        anchor=r['found_from'][0]['anchor'], head=(fetched.get('text_head') or '')[:200]))
    return out


def build_cmd(school, out=None, apply=False):
    if apply:
        reg = Path(out).parent / 'lab-websites.json' if out else P.data_w('lab-websites.json', school)
        cd = json.loads((SCRATCH / school / 'candidates.json').read_text())
        n, lc = apply_register(school, reg, load_fetch(school), cd)
        print(school, 'lab register updated', n, json.dumps(lc))
    doc = build(school, out)
    doc['counts']['pis'] = pi_counts(doc['pis'])
    out = Path(out) if out else P.data_w('person-sweep.json', school)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=0) + '\n')
    print(school, json.dumps(doc['counts']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['harvest', 'fetch', 'build', 'sample'])
    ap.add_argument('school')
    ap.add_argument('--shard', default='0/1')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--out')
    ap.add_argument('--apply', action='store_true', help='build: also close the lab register gaps the fetch resolves')
    a = ap.parse_args()
    i, n = map(int, a.shard.split('/'))
    if a.cmd == 'harvest':
        harvest(a.school)
    elif a.cmd == 'fetch':
        fetch(a.school, (i, n), a.limit)
    elif a.cmd == 'build':
        build_cmd(a.school, a.out, a.apply)
    elif a.cmd == 'sample':
        print(json.dumps(sample(a.school, 30, 20261108, a.out), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
