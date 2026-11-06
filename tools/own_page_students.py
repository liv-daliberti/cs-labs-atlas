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
import collections, gzip, hashlib, html, json, re, sqlite3, sys, time, urllib.parse as U, urllib.request as R
import urllib.robotparser as RP
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pihier.common import norm_title  # noqa: E402
from pihier.names import nick_ok, toks  # noqa: E402

OUT = P.SCRATCH / 'own-pages'
YEARS = (2016, 2025)
MAX_AUTHORS = 15
FEW = 3                                  # a lab with fewer students than this is a target
UA = 'Mozilla/5.0 (compatible; research-atlas-reader)'
SKIP_HOSTS = re.compile(r'(^|\.)(dblp\.org|orcid\.org|scholar\.google\.|linkedin\.com|github\.com|twitter\.com|x\.com|facebook\.com|wikipedia\.org|wikidata\.org|'
                        r'researchgate\.net|semanticscholar\.org|dl\.acm\.org|ieeexplore\.ieee\.org|arxiv\.org|youtube\.com|mathgenealogy|genealogy\.math|academictree\.org|'
                        r'deepblue\.lib\.umich\.edu|news\.umich\.edu|record\.umich\.edu|doi\.org|openreview\.net|ui\.adsabs|loop\.frontiersin|publons|'
                        r'zbmath|scopus\.com|mendeley|acm\.org|ieee\.org|springer\.com|sciencedirect\.com|jstor\.org|aminer|kaggle\.com|gitlab\.com|medium\.com)', re.I)


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
    co = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(name=None, n=0, years=set(), titles=set(), forms=set())))
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
    out = []
    for pi, cs in co.items():
        for k, c in cs.items():
            out.append(dict(pi=pi, pi_names=pi_names.get(pi, [pi]), pi_family_unique=fam[toks(pi_names[pi][0])[-1]] == 1 if pi_names.get(pi) else False,
                            name=c['name'], key=k, n=c['n'], years=sorted(c['years']), titles=sorted(c['titles'])))
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
                res[(s, c['pi'], c['key'])] = list(hit.values())[0]
    return res


def page_urls(p):
    out = []
    for u in p['urls']:
        h = U.urlsplit(u).netloc.lower()
        if u.startswith('http') and h and not SKIP_HOSTS.search(h) and u not in out:
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


def html_text(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg)\b.*?</\1>', ' ', h)
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
    todo = [(k, p) for k, p in sorted(people.items()) if page_urls(p)]
    todo = [x for i, x in enumerate(todo) if i % shard[1] == shard[0]][:limit]
    db = sqlite3.connect(OUT / f'captures-{school}.{shard[0]}.sqlite')
    db.execute('create table if not exists page (cand text, pi text, url text primary key, final text, status text, fetched text, raw_sha256 text, text_sha256 text, text text)')
    db.execute('create table if not exists done (cand text primary key, n integer)')
    done = {r[0] for r in db.execute('select cand from done')}
    for (s, pi, key), p in todo:
        ck = f'{pi}|{key}'
        if ck in done:
            continue
        seen, queue = set(), page_urls(p)[:2]
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
                for href, label in LINKS.findall(r['html']):
                    lab = re.sub(r'<[^>]+>', ' ', label)
                    full = U.urljoin(r.get('final') or u, href.split('#')[0])
                    if (U.urlsplit(full).netloc == host and full.startswith('http') and MORE.search(lab) and not re.search(r'\.(pdf|docx?|zip|png|jpe?g)$', full, re.I)
                            and full not in seen and full not in queue and len(queue) < 3):
                        queue.append(full)
        db.execute('insert or replace into done values (?,?)', (ck, n)); db.commit()
    print(school, 'candidates with a homepage url', len(todo), 'pages', db.execute('select count(*) from page').fetchone()[0],
          'ok', db.execute("select count(*) from page where status='200'").fetchone()[0], 'robots', db.execute("select count(*) from page where status='robots'").fetchone()[0])


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == 'candidates':
        for s in args:
            candidates(s)
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
