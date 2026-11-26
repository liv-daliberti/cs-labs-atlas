"""Sweep of the stored official pages for personal websites (owner request 2026-11-08), feeding tools/person_websites.py.

A URL counts only when an official page, or the person's own verified page, links it; nothing is guessed from a name pattern.

  person_sweep.py harvest <school>                       offline: links beside a person's name on every stored page -> <scratch>/candidates.json
  person_sweep.py queue <school> --labs FILE             the URLs still to fetch -> scratch/websites-b/queue-<school>.jsonl (person_fetch.py reads it)
  person_sweep.py build <school> --labs FILE --out FILE  person-websites.json rows: person_websites.py's plus the sweep's, annotated and gated

Websites only: no student or membership relation changes.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sqlite3
import time
import unicodedata
import zlib
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



# ---------------------------------------------------------------- rows in the person-websites.json format
def sweep_rows(school, labs_path=None):
    """tools/person_websites.py's register for the school, enlarged with the links the sweep found beside a person's name on every
    stored official page (a student's own site, a PI's home page), and with a more specific reason for each person still without a URL."""
    import person_websites as PW
    real_annotate = PW.annotate
    PW.annotate = lambda rows, school: None          # annotate once, after the merge
    try:
        doc = PW.build(school, labs_path)
    finally:
        PW.annotate = real_annotate
    rows = doc['rows']
    data = json.loads((SCRATCH / school / 'candidates.json').read_text())
    domain = school_domain(school)
    _pis, _students, persons = load_people(school)
    have = {(r.get('person_id') or r['person'], PW.original(r['url']).rstrip('/').lower()) for r in rows if r.get('url')}
    have_urls = {(r['person'], r['kind']): r for r in rows if r.get('url')}
    searched = data.get('searched') or {}
    added_students = set()
    for c in data['candidates']:
        host = urlsplit(c['url']).hostname or ''
        if DROP_HOSTS.search(host) or PW.NOT_A_SITE.search(host) or PW.BANNED.search(host):
            continue
        st = classify(c['url'], domain)
        if st in ('news_or_event', 'school_page', 'school_profile', 'lab_member_page'):
            continue
        f = c['found'][0]
        ff = dict(kind='official_page' if (urlsplit(f['page_url']).hostname or '').endswith(('.edu', '.org')) else 'lab_page', url=f['page_url'],
                  sha256=f['page_sha256'], capture_url=f['capture_url'], anchor=f['anchor'])
        key_url = PW.original(c['url']).rstrip('/').lower()
        if c.get('person') is None:           # a PI: only a link whose anchor is the PI's name, found on a page of the school
            if not any(x['how'] == 'anchor_text_is_name' and re.search(domain, urlsplit(x['page_url']).hostname or '') for x in c['found']):
                continue
            kind = 'group' if st == 'lab_site' else 'pi_home'
            if (c['pi'], key_url) in have:
                continue
            old = have_urls.get((c['pi'], kind))
            row = PW.home_row(c['pi'], c['pi'], kind, c['url'], ff, {})
            if old is None:
                rows[:] = [r for r in rows if not (r['person'] == c['pi'] and r['kind'] == 'pi_home' and not r.get('url') and kind == 'pi_home')] if kind == 'pi_home' else rows
            rows.append(row)
            have.add((c['pi'], key_url))
            have_urls[(c['pi'], kind)] = row
            continue
        if not any(x['scope'] == 'page_is_a_recorded_source_of_this_person' for x in c['found']):
            continue
        if (c['person'], key_url) in have:
            continue
        p = persons[c['person']]
        row = PW.home_row(p['name'], sorted(p['pis'])[0], 'student_home', c['url'], ff, {}, role='student') | dict(person_id=c['person'])
        rows.append(row)
        have.add((c['person'], key_url))
        added_students.add(c['person'])
    # a person who gained a URL no longer carries the reason row; the others keep a specific reason
    with_url = {r.get('person_id') for r in rows if r['role'] == 'student' and r.get('url')}
    out = []
    for r in rows:
        if r['role'] == 'student' and not r.get('url'):
            if r.get('person_id') in with_url:
                continue
            pid = r.get('person_id')
            s = searched.get(pid) or []
            if s:
                r['reason'] = (f"no personal-site link beside this person's name on the {len(s)} stored official page(s) that list them "
                               f"(e.g. {'; '.join(sorted({u for u, _ in s})[:2])}); no own page linked from any of them; no name-pattern guess")
            elif pid in persons and all(re.search(r'dspace|figshare|arks\.|dataspace|repository|infoscience|escholarship|thesis', u.split('/')[0]) for u in persons[pid]['sources']) and persons[pid]['sources']:
                r['reason'] = ('listed only by thesis-repository record(s) (' + ', '.join(sorted({u.split('/')[0] for u in persons[pid]['sources']})) +
                               '): a thesis record names the thesis, not a personal site, and the repository is not crawled for links; '
                               'no stored official page lists this person with a link')
        out.append(r)
    doc['rows'] = out
    doc['tool'] = 'tools/person_websites.py + tools/person_sweep.py'
    return doc, real_annotate


def write_queue(school, labs_path):
    import person_websites as PW
    from person_fetch import DIR
    doc, _ = sweep_rows(school, labs_path)
    labs = json.loads(Path(labs_path).read_text())['labs']
    DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(DIR / f'queue-{school}.jsonl', 'w') as f:
        for r in doc['rows']:
            if r.get('url') and not r['fetched'] and r.get('fetch_reason', '').startswith('queued') and not PW.NOT_FETCHABLE.search(urlsplit(r['url']).hostname or ''):
                f.write(json.dumps(dict(url=r['url'], person=r['person'], role=r['role'], kind=r['kind'], lab=r['lab'], mode='live_if_robots_else_wayback')) + '\n')
                n += 1
        for r in labs:
            if r.get('coverage') == 'pending' and r.get('url'):
                f.write(json.dumps(dict(url=r['url'], person=r['pi'], role='pi', kind='lab_pending', lab=r['pi'], gaps=r.get('evidence_gaps'), mode='live_if_robots_else_wayback')) + '\n')
                n += 1
    print(school, 'queued', n)


def write_register(school, labs_path, out):
    import person_websites as PW
    doc, annotate = sweep_rows(school, labs_path)
    annotate(doc['rows'], school)
    bad = PW.gate(doc)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(school, json.dumps(PW.counts(doc)), 'gate_problems', len(bad))
    for b in bad[:5]:
        print('  !', b)
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['harvest', 'queue', 'build'])
    ap.add_argument('school')
    ap.add_argument('--labs', help='lab-websites.json (default: the data path)')
    ap.add_argument('--out')
    a = ap.parse_args()
    labs = a.labs or str(P.data('lab-websites.json', a.school))
    if a.cmd == 'harvest':
        harvest(a.school)
    elif a.cmd == 'queue':
        write_queue(a.school, labs)
    else:
        write_register(a.school, labs, a.out or P.data_w('person-websites.json', a.school))


if __name__ == '__main__':
    main()
