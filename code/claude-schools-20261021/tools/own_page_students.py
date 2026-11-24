"""R-STU-22: a student's own page names the PI as adviser (docs/RULES.md; owner request 2026-11-06).

For a school's PIs with no or few students: the PI's frequent co-authors on lab papers (byline_school: school-affiliated authors, 2016-2025,
at most 15 authors, not faculty in the census) are the candidates; their homepages come from DBLP's own dump (person records: `url` entries
and the ORCID id; the dump, never dblp.org); the page is read live where robots.txt allows (a group naming ClaudeBot / anthropic-ai, any
Crawl-delay and every Disallow are obeyed; generic User-Agent, no e-mail address); only an explicit sentence that this person is or was a
student of this PI at this school becomes evidence (verbatim quote, URL, capture time, sha256).

  own_page_students.py candidates <school>...        co-author candidates          -> <scratch>/own-pages/candidates-<school>.json
  own_page_students.py dblp <school>...              DBLP person records (dump)    -> <scratch>/own-pages/dblp-people.json.gz   (a Slurm job)
  own_page_students.py fetch <school> [--shard i/n]  live pages (robots-checked)   -> <scratch>/own-pages/captures-<school>[.i].sqlite
  own_page_students.py extract <school>              statements                    -> <scratch>/own-pages/proposals-<school>.json
  own_page_students.py evidence <school> [--pilot N] [--write]   -> reviewed/few-students-evidence.json (rows carry rule R-STU-22)

ORCID: pub.orcid.org/robots.txt answers `User-agent: * / Disallow: /` (checked 2026-11-06), so the ORCID public API is not read (no education
records are fetched); the ORCID id DBLP lists for a person is kept only as an identity hint.
"""
import collections, glob, os, zlib, gzip, hashlib, html, json, random, re, sqlite3, sys, time, unicodedata, urllib.parse as U, urllib.request as R
import urllib.robotparser as RP
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pihier.common import norm_title  # noqa: E402
from pihier.names import toks  # noqa: E402

OUT = Path(os.environ.get('OWN_PAGES_OUT') or P.SCRATCH / 'own-pages')   # OWN_PAGES_OUT: a separate working directory (a run for new schools must not overwrite dblp-people.json.gz of the earlier ones)
YEARS = (2016, 2025)
MAX_AUTHORS = 15
FEW = 3                                  # a lab with fewer students than this is a target
UA = 'Mozilla/5.0 (compatible; research-atlas-reader)'
SKIP_HOSTS = re.compile(r'(^|\.)(dblp\.org|orcid\.org|scholar\.google\.|linkedin\.com|github\.com|twitter\.com|x\.com|facebook\.com|wikipedia\.org|wikidata\.org|'
                        r'researchgate\.net|semanticscholar\.org|dl\.acm\.org|ieeexplore\.ieee\.org|arxiv\.org|youtube\.com|mathgenealogy|genealogy\.math|academictree\.org|'
                        r'deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu|doi\.org|openreview\.net|ui\.adsabs|loop\.frontiersin|publons|'
                        r'id\.loc\.gov|zbmath|scopus\.com|mendeley|acm\.org|ieee\.org|springer\.com|sciencedirect\.com|jstor\.org|aminer|kaggle\.com|gitlab\.com|medium\.com)', re.I)


def rd(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    b = p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


def candidates(school):
    """Co-author candidates per target PI (no or few students in the round-2 state)."""
    def d(n):   # the branch's tracked reviewed file where it has one (main's copy is older), else the data path
        w = Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed' / n
        return w if w.exists() else P.data(n, school)
    pis = rd(d('pis.json'))
    stu = rd(d('students.json'), {})
    reasons = rd(d('lab-coverage-reasons.json'), {})
    ev = {}
    for fn in ('few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json', 'roster-evidence.json'):
        for r in rd(d(fn), []) if d(fn).exists() else []:
            ev.setdefault(r['pi'], set()).update(x['name'] for x in r.get('students') or [])
    fac = set()
    for p in pis:
        for n in p['names']:
            fac.add(' '.join(toks(n)))
    fam = collections.Counter(toks(n)[-1] for p in pis for n in p['names'][:1] if toks(n))
    targets = {p['pi'] for p in pis if len({' '.join(toks(x['name'])) for x in stu.get(p['pi']) or []} | {' '.join(toks(x)) for x in ev.get(p['pi'], set())}) < FEW} | set(reasons)
    pi_names = {p['pi']: p['names'] for p in pis}
    co = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(name=None, n=0, years=set(), titles=set(), forms=set(), dois=set())))
    for line in gzip.open(d('lab_papers.jsonl.gz'), 'rt'):
        r = json.loads(line)
        if r['pi'] not in targets or not (YEARS[0] <= (r.get('year') or 0) <= YEARS[1]) or len(r.get('byline') or []) > MAX_AUTHORS:
            continue
        for n in r.get('byline_school') or []:
            t = toks(n)
            if len(t) < 2 or len(t[0]) < 2 or ' '.join(t) in fac or n == r['pi']:
                continue
            c = co[r['pi']][' '.join(t)]
            c['name'] = c['name'] or n; c['n'] += 1; c['years'].add(r['year']); c['forms'].add(n)
            if r.get('title'):
                c['titles'].add(norm_title(r['title']))
            if r.get('doi'):
                c['dois'].add(r['doi'].lower())
    out = []
    for pi, cs in co.items():
        for k, c in cs.items():
            out.append(dict(pi=pi, pi_names=pi_names.get(pi, [pi]), pi_family_unique=fam[toks(pi_names[pi][0])[-1]] == 1 if pi_names.get(pi) else False,
                            name=c['name'], key=k, n=c['n'], years=sorted(c['years']), titles=sorted(c['titles']), dois=sorted(c['dois'])))
    out.sort(key=lambda x: (-x['n'], x['pi'], x['name']))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'candidates-{school}.json').write_text(json.dumps(dict(school=school, targets=sorted(targets), rows=out)))
    print(school, 'targets', len(targets), 'pis with candidates', len(co), 'candidates', len(out), '>=2 papers', sum(x['n'] >= 2 for x in out))


# ---------------------------------------------------------------- DBLP dump (Slurm)
REC = re.compile(r'<(article|inproceedings|proceedings|book|incollection|phdthesis|mastersthesis|www|data) ([^>]*?)key="([^"]+)"[^>]*>(.*?)</\1>', re.S)
AUTH = re.compile(r'<(?:author|editor)([^>]*)>(.*?)</(?:author|editor)>', re.S)
URL = re.compile(r'<url[^>]*>(.*?)</url>')
NOTE = re.compile(r'<note[^>]*type="([^"]+)"[^>]*>(.*?)</note>', re.S)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S)
YEAR = re.compile(r'<year>(\d{4})</year>')


def text(s):
    return re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()


def base(name):
    return ' '.join(toks(re.sub(r'\s+\d{4}$', '', name)))


def records():
    tail = ''
    with gzip.open(P.DBLP_DUMP_XML, 'rt', encoding='utf-8', errors='replace') as f:
        while True:
            chunk = f.read(8 << 20); buf = tail + chunk; end = 0
            for m in REC.finditer(buf):
                end = m.end(); yield m.group(1), m.group(3), m.group(4)
            tail = buf[end:]
            if not chunk:
                break


def dblp(schools):
    """One pass over DBLP's dump: the person records carrying a candidate's name, and the publication records whose title is a lab paper's.
    A person is the candidate when one of their DBLP name strings is on a record whose title is a lab paper the candidate co-authored."""
    names, titles = set(), set()
    for s in schools:
        for r in rd(OUT / f'candidates-{s}.json')['rows']:
            names.add(base(r['name'])); titles.update(r['titles'])
    persons, pubs = [], []
    for typ, key, body in records():
        if typ == 'www':
            if not key.startswith('homepages/'):
                continue
            ns = [text(a) for _, a in AUTH.findall(body)]
            if any(base(n) in names for n in ns):
                urls = [text(u) for u in URL.findall(body)]
                persons.append(dict(pid=key.split('/', 1)[1], names=ns, urls=urls, affiliations=[text(v) for t, v in NOTE.findall(body) if t == 'affiliation'],
                                    orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m})))
        elif typ != 'data':
            t = TITLE.search(body)
            if t and norm_title(text(t.group(1))) in titles:
                y = YEAR.search(body)
                pubs.append(dict(key=key, title=norm_title(text(t.group(1))), year=int(y.group(1)) if y else None, authors=[text(a) for _, a in AUTH.findall(body)]))
    with gzip.open(OUT / 'dblp-people.json.gz', 'wt') as f:
        json.dump(dict(dump=P.DBLP_DUMP_XML.name, persons=persons, pubs=pubs), f, ensure_ascii=False)
    print(json.dumps(dict(persons=len(persons), pubs=len(pubs))))


def homepages(schools):
    """candidate -> {urls, orcid, pids}: the DBLP person whose name string is on a pub record with one of the candidate's lab paper titles."""
    dd = rd(OUT / 'dblp-people.json.gz')
    by_str = collections.defaultdict(list)
    for p in dd['persons']:
        for n in p['names']:
            by_str[n].append(p)
    by_title = collections.defaultdict(list)
    for r in dd['pubs']:
        by_title[r['title']].append(r)
    res = {}
    for s in schools:
        for c in rd(OUT / f'candidates-{s}.json')['rows']:
            hit = {}
            for t in c['titles']:
                for pub in by_title.get(t, []):
                    for a in pub['authors']:
                        if base(a) == base(c['name']) or base(a) == c['key']:
                            for p in by_str.get(a, []):
                                hit[p['pid']] = p
            if len(hit) == 1:   # exactly one DBLP person: otherwise two homonyms share the lab papers' title set
                res[(s, c['pi'], c['key'])] = dict(list(hit.values())[0])
            hp = (rd(OUT / f'hop-{s}.json', {}).get(c['key']) or []) + (rd(OUT / f's2-{s}.json', {}).get(c['key']) or [])
            if hp:   # a link on a stored lab page whose text is the candidate's full name
                p = res.setdefault((s, c['pi'], c['key']), dict(pid=None, names=[c['name']], urls=[], affiliations=[], orcid=[]))
                p['urls'] = list(p['urls']) + [u for u in hp if u not in p['urls']]
    return res


def hop(school):
    """Homepage links on the stored lab pages (the lab-page audit's captures): an anchor whose text is a candidate's full name and whose target is
    not a profile host. -> hop-<school>.json {name key: [urls]}"""
    want = {c['key'] for c in rd(OUT / f'candidates-{school}.json')['rows']}
    db = sqlite3.connect(f"file:{P.data('labpage-audit-captures.sqlite', school)}?mode=ro", uri=True)
    found = collections.defaultdict(set)
    for url, ctype, blob in db.execute("select url, content_type, content from captures where status=200"):
        if 'html' not in (ctype or ''):
            continue
        try:
            h = zlib.decompress(blob).decode('utf8', 'replace')
        except Exception:  # noqa: BLE001
            continue
        for href, label in LINKS.findall(content_html(h)):
            k = ' '.join(toks(html.unescape(re.sub(r'<[^>]+>', ' ', label))))
            if k not in want:
                continue
            m = re.search(r'/web/\d+(?:id_|im_|if_)?/(https?://.*)', href)
            u = m.group(1) if m else href
            if u.startswith('http') and not SKIP_HOSTS.search(U.urlsplit(u).netloc) and not re.search(r'\.(pdf|jpe?g|png)$', u, re.I):
                found[k].add(u)
    out = {k: sorted(v)[:3] for k, v in found.items()}
    (OUT / f'hop-{school}.json').write_text(json.dumps(out))
    print(school, 'hop names', len(out))


def s2_homepages(school):
    """Semantic Scholar's paper batch (graph API, the project's key from ~/.config/cs-atlas/s2.env, never printed; 1 request a second, 500 papers a request):
    the authors of the lab papers with the homepage their S2 profile lists; an author is the candidate when the name matches in full.
    -> s2-<school>.json {name key: [homepage urls]}"""
    env = Path.home() / '.config' / 'cs-atlas' / 's2.env'
    key = dict(x.split('=', 1) for x in env.read_text().split('\n') if '=' in x).get('S2_API_KEY', '').strip()
    rows = [c for c in rd(OUT / f'candidates-{school}.json')['rows'] if c['n'] >= 2]
    by_doi = collections.defaultdict(list)
    for c in rows:
        for d in c['dois']:
            by_doi[d].append(c)
    dois = sorted(by_doi)
    out = rd(OUT / f's2-{school}.json', {})
    for i in range(0, len(dois), 500):
        chunk = dois[i:i + 500]
        req = R.Request('https://api.semanticscholar.org/graph/v1/paper/batch?fields=authors.name,authors.homepage',
                        data=json.dumps(dict(ids=['DOI:' + d for d in chunk])).encode(), headers={'Content-Type': 'application/json', 'x-api-key': key, 'User-Agent': UA})
        for attempt in range(8):   # the key is shared with the other agents: a 429 backs off a minute at a time
            try:
                with R.urlopen(req, timeout=120) as r:
                    res = json.loads(r.read())
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 7:
                    raise
                time.sleep(60 * (attempt + 1) if getattr(e, 'code', 0) == 429 else 10)
        for d, paper in zip(chunk, res):
            for a in (paper or {}).get('authors') or []:
                hp = (a.get('homepage') or '').strip()
                if not hp.startswith('http') or SKIP_HOSTS.search(U.urlsplit(hp).netloc):
                    continue
                k = ' '.join(toks(a.get('name') or ''))
                for c in by_doi[d]:
                    if c['key'] == k:
                        out.setdefault(k, [])
                        if hp not in out[k]:
                            out[k].append(hp)
        time.sleep(1.2)
    (OUT / f's2-{school}.json').write_text(json.dumps(out))
    print(school, 'papers', len(dois), 's2 homepages', len(out))


CLOSED = {}   # school -> hosts whose charter host_use is `none` (never contacted; hosts.json, written by school_hosts.py)


def closed_hosts(school):
    if school not in CLOSED:
        try:
            hs = json.load(open(P.data('hosts.json', school))).get('hosts') or []
        except Exception:  # noqa: BLE001
            hs = []
        CLOSED[school] = {h['host'].lower() for h in hs if h.get('use') == 'none'}
    return CLOSED[school]


def page_urls(p, school=None):
    out = []
    closed = closed_hosts(school) if school else set()
    for u in p['urls']:
        h = U.urlsplit(u).netloc.lower()
        if u.startswith('http') and h and not SKIP_HOSTS.search(h) and h not in closed and u not in out:
            out.append(u)
    return out


# ---------------------------------------------------------------- live fetch
class Robots:
    def __init__(self):
        self.cache = {}
        self.last = {}

    def rules(self, host, scheme):
        if host not in self.cache:
            rp = RP.RobotFileParser()
            raw, status = '', None
            try:
                req = R.Request(f'{scheme}://{host}/robots.txt', headers={'User-Agent': UA})
                with R.urlopen(req, timeout=20) as r:
                    raw = r.read(500000).decode('utf8', 'replace'); status = r.status
            except Exception as e:  # noqa: BLE001
                status = getattr(e, 'code', None)
                if status is None:
                    self.cache[host] = (None, 0, 'error')   # unreachable: do not fetch
                    return self.cache[host]
            rp.parse(raw.splitlines()) if status == 200 else None
            ai = False
            if status == 200:   # any group naming an AI crawler that disallows anything bars the host
                for grp in re.split(r'\n\s*\n', raw):
                    if re.search(r'user-agent:\s*(claudebot|anthropic-ai|claude-web)', grp, re.I) and re.search(r'^\s*disallow:\s*\S', grp, re.I | re.M):
                        ai = True
            delay = rp.crawl_delay('*') if status == 200 else None
            self.cache[host] = (rp if status == 200 else ('open' if status in (404, 410) else None), float(delay or 0), 'ai_group' if ai else 'ok')
        return self.cache[host]

    def allowed(self, url):
        sp = U.urlsplit(url)
        rp, delay, flag = self.rules(sp.netloc, sp.scheme)
        if flag != 'ok' or rp is None:
            return False, delay
        return (True if rp == 'open' else rp.can_fetch('*', url)), delay

    def wait(self, host, delay):
        gap = max(3.0, delay)
        t = time.time() - self.last.get(host, 0)
        if t < gap:
            time.sleep(gap - t)
        self.last[host] = time.time()


LINKS = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)
MORE = re.compile(r'\b(cv|curriculum vitae|vita|about|bio|biography|people|students?|members?|team|group|home)\b', re.I)


def content_html(h):
    """Remove comments and non-content blocks before reading text or links."""
    h = re.sub(r'(?s)<!--.*?(?:-->|$)', ' ', h)
    h = re.sub(r'(?is)<(script|style|noscript|svg)\b.*?</\1>', ' ', h)
    return h


def html_text(h):
    h = content_html(h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|li|tr|h\d|ul|ol|section|article|table|dd|dt)>', '\n', h)
    h = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    return '\n'.join(re.sub(r'[ \t\xa0]+', ' ', ln).strip() for ln in h.split('\n') if ln.strip())


def get(url, rb):
    ok, delay = rb.allowed(url)
    if not ok:
        return dict(url=url, status='robots' if delay is not None else 'error', text='', raw_sha256=None)
    rb.wait(U.urlsplit(url).netloc, delay)
    try:
        with R.urlopen(R.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html'}), timeout=25) as r:
            ctype = r.headers.get('Content-Type', '')
            raw = r.read(3_000_000)
            final = r.geturl()
        if 'html' not in ctype.lower():
            return dict(url=url, status='not_html', text='', raw_sha256=None)
        h = raw.decode('utf8', 'replace')
        return dict(url=url, final=final, status=200, html=h, text=html_text(h), raw_sha256=hashlib.sha256(raw).hexdigest())
    except Exception as e:  # noqa: BLE001
        return dict(url=url, status=str(getattr(e, 'code', type(e).__name__)), text='', raw_sha256=None)


def fetch(school, shard=(0, 1), limit=None):
    rb = Robots()
    people = homepages([school])
    todo = [(k, p) for k, p in sorted(people.items()) if page_urls(p, school)]
    todo = [x for x in todo if zlib.crc32(U.urlsplit(page_urls(x[1], school)[0]).netloc.encode()) % shard[1] == shard[0]][:limit]   # a host belongs to one shard: its pacing holds
    db = sqlite3.connect(OUT / f'captures-{school}.{shard[0]}.sqlite')
    db.execute('create table if not exists page (cand text, pi text, url text primary key, final text, status text, fetched text, raw_sha256 text, text_sha256 text, text text)')
    db.execute('create table if not exists done (cand text primary key, n integer)')
    done = {r[0] for r in db.execute('select cand from done')}
    for (s, pi, key), p in todo:
        ck = f'{pi}|{key}'
        if ck in done:
            continue
        seen, queue = set(), page_urls(p, school)[:2]
        n = 0
        while queue and n < 4:
            u = queue.pop(0)
            if u in seen:
                continue
            seen.add(u)
            r = get(u, rb); n += 1
            txt = r.get('text') or ''
            db.execute('insert or replace into page values (?,?,?,?,?,?,?,?,?)',
                       (ck, pi, u, r.get('final'), str(r['status']), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), r.get('raw_sha256'),
                        hashlib.sha256(txt.encode()).hexdigest() if txt else None, txt))
            if r['status'] == 200 and n <= 2:   # a CV / about / people link on the same host
                host = U.urlsplit(r.get('final') or u).netloc
                for href, label in LINKS.findall(content_html(r['html'])):
                    lab = re.sub(r'<[^>]+>', ' ', label)
                    full = U.urljoin(r.get('final') or u, href.split('#')[0])
                    if (U.urlsplit(full).netloc == host and full.startswith('http') and MORE.search(lab) and not re.search(r'\.(pdf|docx?|zip|png|jpe?g)$', full, re.I)
                            and full not in seen and full not in queue and len(queue) < 3):
                        queue.append(full)
        db.execute('insert or replace into done values (?,?)', (ck, n)); db.commit()
    print(school, 'candidates with a homepage url', len(todo), 'pages', db.execute('select count(*) from page').fetchone()[0],
          'ok', db.execute("select count(*) from page where status='200'").fetchone()[0], 'robots', db.execute("select count(*) from page where status='robots'").fetchone()[0])


# ---------------------------------------------------------------- extraction: an explicit statement only
CUE = re.compile(r"(co-?\s?advis(?:ed|or|er)s?|advis(?:ed|or|er)s?|supervis(?:ed|or|ors)|(?:under|with)\s+(?:the\s+)?(?:guidance|supervision|direction|mentorship)\s+of|"
                 r"thesis\s+committee\s+chair|my\s+(?:phd\s+)?(?:advisor|adviser|supervisor))", re.I)
STUDENT = re.compile(r"(ph\.?\s?d\.?|doctoral|doctorate|graduate\s+student|grad\s+student|m\.?\s?s\.?\b|master'?s|masters|undergraduate|b\.?\s?s\.?\b|bachelor|"
                     r"student|candidate)", re.I)
BAD = re.compile(r"(\bintern\b|post-?\s?doc|postdoctoral|research\s+scientist|research\s+associate|visiting\s+(?:professor|scholar|researcher|faculty)|collaborat|co-author|joint\s+work|"
                 r"spent\s+(?:a\s+)?(?:summer|semester)|intern(?:ed|ship)\s+(?:at|with))", re.I)
OTHER = re.compile(r"(\buniversity\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+University\b|institute\s+of\s+technology|\bMIT\b|\bcaltech\b|"
                   r"\bstanford\b|\bberkeley\b|\bCMU\b|carnegie\s+mellon|\bharvard\b|\bprinceton\b|\bepfl\b|\beth\s+zurich\b|\btsinghua\b|\bpeking\b|\bIIT\s+\w+|\bUCLA\b|\bUCSD\b|\bUCSB\b|\bNYU\b)")
PAST = re.compile(r"\b(previously|prior\s+to|got\s+my|finished|did\s+my|where\s+i\s+(?:was|worked)|(?:co-?)?advised\s+by.{0,80}\bwhere|was\s+(?:co-?)?advised|were\s+(?:co-?)?advised|worked\s+under|(?:i|he|she)\s+(?:was|were)\b|graduated|received|earned|defended|former|alumn\w*|obtained|completed|was\s+a|were|class\s+of|joined\s+\w+\s+as|now\s+(?:a|an|at)|currently\s+(?:a|an)\s+(?:assistant|associate|professor|postdoc|research|software|engineer|scientist))\b", re.I)
NOW = re.compile(r"\b(currently|final[- ]year|(?:first|second|third|fourth|fifth|sixth|\d(?:st|nd|rd|th))[- ]year|rising|incoming|i\s+am\s+a|i'?m\s+a|is\s+a|am\s+a|expected|expecting|candidate|present|ongoing)\b|\b(?:19|20)\d\d\s*[-\u2013\u2014]+\s*(?:present|now|current|ongoing)", re.I)
MONTH = r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?"
RANGE = re.compile(r"((?:19|20)\d\d)\s*(?:[-\u2013\u2014]+|to)\s*" + MONTH + r"((?:19|20)\d\d|present|now|current|ongoing)", re.I)
SINCE = re.compile(r"\b(?:since|starting(?:\s+from)?|started(?:\s+in)?|joined\s+(?:\w+\s+){0,3}in)\s+(?:(?:the\s+)?(?:spring|summer|fall|autumn|winter)\s+(?:of\s+)?)?((?:19|20)\d\d)", re.I)
YR = re.compile(r"(?<!\d)((?:19|20)\d\d)(?!\d)")
CAPTURE_YEAR = int(time.strftime('%Y'))


def fold(s):
    s = unicodedata.normalize('NFKD', (s or '').replace('\u2019', "'").replace('\u2018', "'"))
    return ''.join(c for c in s if not unicodedata.combining(c))


def pi_regex(c):
    """The PI's written forms: given name (or a nickname) + family name, optional middle initials; a bare family name only with a title and when no other
    faculty member of the school has it."""
    forms = []
    for n in c['pi_names']:
        t = toks(n)
        if len(t) >= 2:
            forms.append(r'\b' + re.escape(t[0]) + r"(?:\s+[a-z]\.?){0,2}\s+" + re.escape(t[-1]) + r'\b')
            forms.append(r'\b' + re.escape(t[0][0]) + r'\.?\s*(?:[a-z]\.?\s*){0,2}' + re.escape(t[-1]) + r'\b')
    fam = toks(c['pi_names'][0])[-1] if c['pi_names'] else ''
    if c.get('pi_family_unique') and fam:
        forms.append(r'\b(?:prof(?:essor)?|dr)\.?\s+(?:[a-z]+\s+)?' + re.escape(fam) + r'\b')
    return re.compile('|'.join(forms), re.I) if forms else None


def cand_regex(c):
    t = toks(c['name'])
    return re.compile(r'\b' + re.escape(t[0]) + r"(?:\s+[a-z]+\.?){0,2}\s+" + re.escape(t[-1]) + r'\b', re.I)


GAP_WORDS = {'by', 'and', 'is', 'are', 'was', 'were', 'of', 'the', 'prof', 'professor', 'professors', 'dr', 'drs', 'advisors', 'advisor', 'adviser', 'advisers',
             'co', 'include', 'includes', 'my', 'at', 'in', 'a', 'her', 'his', 'their', 'been', 'be', 'to', 'fortunate', 'lucky', 'luckily', 'currently', 'jointly', 'supervisor', 'supervisors', 'phd'}


def gap_ok(gap):
    """The text between the adviser cue and the PI's name holds names, titles and 'and' only: 'advised by A, and worked closely with <PI>' does not make the PI an adviser."""
    if re.search(r'committee|reader|member|collaborat|examiner', gap, re.I):   # 'Adviser: A Committee: <PI>' names the PI as a committee member
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", re.sub(r'\b[A-Z][\w\-\'.]*', ' ', gap))   # capitalized words (names, titles) removed
    return all(w.lower() in GAP_WORDS for w in words)


ROLES = [('visiting', r'visiting\s+(?:ph\.?d\.?\s+|graduate\s+|master\S*\s+|undergraduate\s+)?student|exchange\s+student'), ('phd', r'ph\.?\s?d|doctoral|doctorate|graduate\s+student|grad\s+student'),
         ('masters', r"\bm\.?\s?s\.?\b|master'?s|masters"), ('undergraduate', r'undergrad\w*|\bb\.?\s?s\.?\b|bachelor')]


def role_near(t, pos):
    """The role cue before the adviser cue; cues within 60 characters of the nearest one compete by rank ('Ph.D. and M.S.' is a PhD); none before: the nearest after."""
    found = [(x.start(), i, role) for i, (role, rx) in enumerate(ROLES) for x in re.finditer(rx, t, re.I)]
    before = [f for f in found if f[0] < pos]
    if before:
        last = max(f[0] for f in before)
        return min((f for f in before if last - f[0] <= 60), key=lambda f: f[1])[2]
    after = sorted(f for f in found if f[0] >= pos)
    return after[0][2] if after else None


def role_in(sent, pos):
    """The role cues before the adviser cue in its own sentence; the highest one wins ('Ph.D. and M.S. at X, advised by Y' is a PhD)."""
    t = sent[:pos]
    for role, rx in ROLES:
        if re.search(rx, t, re.I):
            return role
    return None


def sentences(ln):
    """A line split into sentences; 'Prof.', 'Dr.' and single-letter initials ('H. V. Jagadish') do not end one."""
    t = re.sub(r'\b(Prof|Dr|Mr|Ms|Mrs|St|vs|etc|e\.g|i\.e)\.', lambda m: m.group(1) + '\x00', ln)
    t = re.sub(r'\b([A-Z])\.', lambda m: m.group(1) + '\x00', t)
    return [x.replace('\x00', '.') for x in re.split(r'(?<=[a-z0-9\)\]])\s?[.!?]\s+(?=[A-Z])', t) if x.strip()]


def statements(c, text, rx_school):
    """The explicit advisee statements of one page for one (PI, candidate): [{quote, role, years, years_basis, alumni}].
    The sentence with the adviser cue must name the PI right after the cue; the institution nearest before the cue (this sentence, else the one
    before, else the lines above) must be the school; a student cue is in the scope; a postdoc / collaborator cue near the cue rejects."""
    prx, crx = pi_regex(c), cand_regex(c)
    if not prx or not crx.search(fold(text)):    # namesake guard: the page must name the candidate in full (given + family)
        return []
    lines = text.split('\n')
    out = []
    ys_ = [int(y) for y in YR.findall(text) if int(y) <= CAPTURE_YEAR]
    fresh = bool(ys_) and max(ys_) >= CAPTURE_YEAR - 3     # R-LAB-02: a page whose newest year is old is a stale undated list: no capture-year inference
    for i, ln in enumerate(lines):
        osents = sentences(ln)
        sents = [fold(x) for x in osents]
        for j, sent in enumerate(sents):
            for m in CUE.finditer(sent):
                seg = sent[m.start():m.end() + 140]
                pm = prx.search(seg)
                if not pm or not gap_ok(seg[m.end() - m.start():pm.start()]):
                    continue
                pre = sents[j - 1] if j else fold(' '.join(lines[max(0, i - 2):i]))
                nxt = sents[j + 1] if j + 1 < len(sents) else (fold(lines[i + 1]) if i + 1 < len(lines) else '')
                scope = pre + ' ' + sent + ' ' + nxt
                cue_pos = len(pre) + 1 + m.start()
                if BAD.search(sent[max(0, m.start() - 120):m.end() + 160]):
                    continue
                mk = lambda t: rx_school.sub('SCHOOLMENTION', t)  # noqa: E731
                mpre, msent = mk(pre), mk(sent)
                masked = mpre + ' ' + msent
                cp = len(mpre) + 1 + len(mk(sent[:m.start()]))      # the cue's position in the masked text
                marks = [(x.start(), True) for x in re.finditer('SCHOOLMENTION', masked)] + [(x.start(), False) for x in OTHER.finditer(masked)]
                before = [x for x in marks if x[0] < cp]
                after = [x for x in marks if x[0] >= cp and x[0] > len(mpre)]
                near = max(before) if before else (min(after) if after else None)   # the institution the cue's clause belongs to
                if near is None or not near[1]:
                    continue
                if not STUDENT.search(scope):
                    continue
                role = role_in(sent, m.start()) or role_near(pre + ' ' + sent, len(pre) + 1 + m.start())
                if not role:
                    continue
                now = (bool(NOW.search(pre + ' ' + sent)) or bool(re.search(r'student|candidate', sent, re.I))) and not PAST.search(pre + ' ' + sent) and fresh
                rgs = sorted((abs(x.start() - near[0]), x) for x in RANGE.finditer(masked) if abs(x.start() - near[0]) <= 150 and (x.start() < len(mpre)) == (near[0] < len(mpre)))
                rg = rgs[0][1] if rgs else None   # a range written next to the school mention, in this sentence or the one before
                years, basis = None, None
                if rg:
                    a_ = int(rg.group(1)); b_ = rg.group(2).lower()
                    b_ = CAPTURE_YEAR if not b_.isdigit() else int(b_)
                    if a_ <= b_:
                        years, basis = [a_, b_], 'stated'
                if years is None and now:
                    sm = SINCE.search(pre + ' ' + sent)
                    years, basis = ([int(sm.group(1)), CAPTURE_YEAR], 'stated') if sm and int(sm.group(1)) <= CAPTURE_YEAR else ([CAPTURE_YEAR, CAPTURE_YEAR], 'capture_date')
                if years is None:   # a degree year written next to the school mention (within 120 characters), the nearest one
                    lo, hi = (0, len(mpre)) if near[0] < len(mpre) else (len(mpre) + 1, len(masked))   # only the sentence that holds the school mention
                    ys = sorted((abs(x.start() - near[0]), int(x.group(1))) for x in YR.finditer(masked) if lo <= x.start() < hi and abs(x.start() - near[0]) <= 120)
                    if ys and re.search(r'ph\.?\s?d|m\.?\s?s\b|b\.?\s?s\b|degree|graduat|defen|thesis|dissertation|received|earned|doctor', pre + ' ' + sent, re.I):
                        years, basis = [ys[0][1]], 'stated_degree_year'
                if years is None and not now:
                    years, basis = None, 'undated_alumnus'    # an explicit statement, no year on the page: listed apart, never evidence (R-STU-14)
                years_in_sent = bool(YR.search(sent))
                if years is None and basis != 'undated_alumnus':
                    continue
                if years and (years[-1] < YEARS[0] or years[0] > CAPTURE_YEAR):
                    continue
                oq = ((osents[j - 1] if j else ' '.join(lines[max(0, i - 2):i])) + ' ') if (near[0] < len(mpre) or (not years_in_sent and len(sent) < 80)) else ''
                q = re.sub(r'\s+', ' ', oq + osents[j]).strip()
                if len(q) > 520:
                    ci = len(oq) + m.start()
                    q = q[max(0, ci - 320):ci + 200]
                out.append(dict(quote=q, role=role, years=years, years_basis=basis, alumni=not now, school_nearest=True))
    return out


def extract(school):
    cands = {(c['pi'], c['key']): c for c in rd(OUT / f'candidates-{school}.json')['rows']}
    rx = S.aff_rx(school)
    rows = []
    stat = collections.Counter()
    for f in sorted(glob.glob(str(OUT / f'captures-{school}.*.sqlite'))):
        db = sqlite3.connect(f)
        by = collections.defaultdict(list)
        for ck, pi, url, final, status, fetched, rsha, tsha, txt in db.execute("select cand,pi,url,final,status,fetched,raw_sha256,text_sha256,text from page where status='200'"):
            by[ck].append((url, final, fetched, rsha, tsha, txt))
        for ck, pages in by.items():
            pi, key = ck.split('|', 1)
            c = cands.get((pi, key))
            if not c:
                continue
            stat['candidates_with_pages'] += 1
            for url, final, fetched, rsha, tsha, txt in pages:
                for st in statements(c, txt, rx):
                    rows.append(dict(pi=pi, name=c['name'], key=key, n_papers=c['n'], paper_years=c['years'], url=final or url, fetched=fetched, sha256=tsha, raw_sha256=rsha, **st))
                    stat['statements'] += 1
    # one row per (pi, name): the first statement; a student named on two pages keeps the page with stated years
    best = {}
    for r in rows:
        k = (r['pi'], r['key'])
        rank = lambda x: ({'stated': 0, 'stated_degree_year': 1, 'capture_date': 2, 'undated_alumnus': 3}[x['years_basis']], ['phd', 'visiting', 'masters', 'undergraduate'].index(x['role']))  # noqa: E731
        if k not in best or rank(r) < rank(best[k]):
            best[k] = r
    rows = sorted(best.values(), key=lambda r: (r['pi'], r['name']))
    (OUT / f'proposals-{school}.json').write_text(json.dumps(dict(school=school, stats=dict(stat), rows=rows), ensure_ascii=False, indent=1))
    print(school, dict(stat), 'rows', len(rows), 'pis', len({r['pi'] for r in rows}), 'dated', sum(r['years_basis'] != 'undated_alumnus' for r in rows), 'undated alumni', sum(r['years_basis'] == 'undated_alumnus' for r in rows))


def evidence(school, pilot=None, write=False, seed=20261106):
    """Proposals -> evidence rows (R-STU-22). --pilot N prints N random rows for reading; --write merges all rows into the branch's
    reviewed/few-students-evidence.json (the tracked file of the worktree)."""
    prop = rd(OUT / f'proposals-{school}.json')['rows']
    wt = Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed' / 'few-students-evidence.json'
    cur = rd(wt, []) if wt.exists() else []
    have = {(r['pi'], ' '.join(toks(x['name']))) for r in cur for x in r.get('students') or []}
    rows = []
    for r in prop:
        if (r['pi'], ' '.join(toks(r['name']))) in have:
            continue
        if r['years_basis'] == 'undated_alumnus':   # owner 2026-11-06: years of the co-authored lab papers with this PI (2016-2025); none, no row
            py = [y for y in r.get('paper_years') or [] if YEARS[0] <= y <= YEARS[1]]
            if not py:
                continue
            r = dict(r, years=[min(py), max(py)], years_basis='coauthored_lab_papers')
        rows.append(r)
    if pilot:
        random.Random(seed).shuffle(rows)
        rows = rows[:pilot]
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    by = {r['pi']: r for r in cur}
    for r in rows:
        e = by.setdefault(r['pi'], dict(pi=r['pi'], students=[]))
        e['students'] = [x for x in e['students'] if not (x.get('rule') == 'R-STU-22' and ' '.join(toks(x['name'])) == ' '.join(toks(r['name'])))]
        disp = ' '.join(reversed([x.strip() for x in r['name'].split(',', 1)])) if ',' in r['name'] else r['name']   # 'Nief, Todd' -> 'Todd Nief'
        e['students'].append(dict(name=disp, role=r['role'], years=r['years'], years_basis=r['years_basis'], alumni=r['alumni'],
                                  section="student's own page names the PI as adviser (R-STU-22)", url=r['url'], capture_url=r['url'], captured=r['fetched'],
                                  sha256=r['sha256'], raw_sha256=r['raw_sha256'], quote=r['quote'], auto=True, rule='R-STU-22', source='own_page'))
    if write:
        wt.write_text(json.dumps(list(by.values()), ensure_ascii=False, indent=1))   # the file's own style: indent 1, no trailing newline, existing order
    print(school, 'rows', len(rows), 'pis', len({r['pi'] for r in rows}), 'written' if write else 'dry run')


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'candidates':
        for s in args:
            candidates(s)
    elif cmd == 'evidence':
        pl = None
        if '--pilot' in args:
            pl = int(args[args.index('--pilot') + 1])
        evidence(args[0], pl, '--write' in args)
    elif cmd == 's2':
        for s_ in args:
            s2_homepages(s_)
    elif cmd == 'hop':
        for s_ in args:
            hop(s_)
    elif cmd == 'extract':
        extract(args[0])
    elif cmd == 'dblp':
        dblp(args)
    elif cmd == 'fetch':
        sh = (0, 1)
        if '--shard' in args:
            i = args.index('--shard'); a, b = args[i + 1].split('/'); sh = (int(a), int(b)); del args[i:i + 2]
        lim = None
        if '--limit' in args:
            i = args.index('--limit'); lim = int(args[i + 1]); del args[i:i + 2]
        fetch(args[0], sh, lim)
    else:
        sys.exit(__doc__)
