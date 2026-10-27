"""Recover lab papers that a PI's own DBLP person page lists but the hierarchy lacks (missing_papers_audit.py's gap).

For each DBLP publication (2016-2026, not a CoRR preprint) of a PI with a DBLP id, in a year the PI's appointment
covers, not already among the PI's lab papers:
  doi      OpenAlex record by DOI (singleton lookups are free): the PI's authorship (name match) listing the school
           -> basis 'openalex_authorship'. An authorship listing only other institutions is left out.
  page 1   otherwise the paper's own first page must tie the school to the PI (pi_fulltext_affiliation.tie: affiliation
           marker, author block, or the only institution named):
             arXiv   the DBLP CoRR record of the same title by the same PI (key journals/corr/abs-YYMM-NNNNN), an arxiv.org
                     link among the record's ee, or an arXiv location in OpenAlex; version 1 from arXiv's public bulk copy
             open    an open PDF among the record's ee / OpenAlex locations on a proceedings host (ACL Anthology, PMLR,
                     CVF, NeurIPS, USENIX, IJCAI, AAAI, OpenReview...), robots.txt honoured, 3 s per host
           -> basis 'page1_arxiv' / 'page1_open'
The DBLP record is the PI's own publication list, so it is the identity anchor; the appointment rule still applies
when the hierarchy is built.
-> hierarchy/<school>/dblp-recovered.jsonl (one row per accepted paper) and dblp-recover.sqlite (every attempt, the
   page-1 text and PDF sha256)
usage: dblp_recover.py <school> [--workers 6]
"""
import collections, gzip, hashlib, json, os, re, sqlite3, subprocess, sys, tempfile, threading, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
import requests

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import read, HERE, DBLP, INST, AFF, ndoi, norm_title, Name, toks, given  # noqa: E402
from pi_fulltext_affiliation import tie  # noqa: E402

UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
OPEN_HOSTS = ('aclanthology.org', 'proceedings.mlr.press', 'openaccess.thecvf.com', 'papers.nips.cc', 'proceedings.neurips.cc',
              'www.usenix.org', 'usenix.org', 'www.ijcai.org', 'ojs.aaai.org', 'openreview.net', 'www.isca-speech.org',
              'www.roboticsproceedings.org', 'roboticsproceedings.org', 'jmlr.org', 'www.jmlr.org', 'dl.acm.org/doi/pdf')
_last = collections.defaultdict(float); _lock = threading.Lock(); _robots = {}


def polite_get(url, delay=3.0):
    host = urlsplit(url).netloc
    if host not in _robots:
        try:
            rb = requests.get(f'https://{host}/robots.txt', headers={'User-Agent': UA}, timeout=20)
            _robots[host] = rb.text if rb.status_code == 200 else ''
        except requests.RequestException:
            _robots[host] = ''
    path = urlsplit(url).path
    dis = [l.split(':', 1)[1].strip() for l in _robots[host].splitlines() if l.lower().startswith('disallow:')]
    if any(d and path.startswith(d) for d in dis):  # crude but conservative: any Disallow prefix, for any agent
        return None
    with _lock:
        wait = _last[host] + delay - time.time(); _last[host] = max(time.time(), _last[host] + delay)
    if wait > 0:
        time.sleep(wait)
    try:
        return requests.get(url, headers={'User-Agent': UA}, timeout=90)
    except requests.RequestException:
        return None


def pdf_url(u):
    """A proceedings landing page -> its PDF (the hosts' own URL patterns), else the URL if it already is a PDF."""
    u = u.replace('http://', 'https://')
    if 'aclanthology.org' in u:
        return u.rstrip('/') + ('' if u.endswith('.pdf') else '.pdf')
    m = re.match(r'(https://proceedings\.mlr\.press/v\d+/)([\w\-]+)\.html$', u)
    if m:
        return f'{m.group(1)}{m.group(2)}/{m.group(2)}.pdf'
    if 'openaccess.thecvf.com' in u and '/html/' in u and u.endswith('.html'):
        return u.replace('/html/', '/papers/').replace('_paper.html', '_paper.pdf').replace('.html', '.pdf')
    m = re.match(r'https://(?:papers\.nips\.cc|proceedings\.neurips\.cc)/paper(?:_files/paper)?/(\d{4})/hash/(\w+)-Abstract(?:-Conference|-Datasets_and_Benchmarks)?\.html', u)
    if m:
        kind = 'Paper-Conference' if 'Conference' in u else 'Paper'
        return f'https://proceedings.neurips.cc/paper_files/paper/{m.group(1)}/file/{m.group(2)}-{kind}.pdf'
    m = re.match(r'https://openreview\.net/forum\?id=([\w\-]+)', u)
    if m:
        return f'https://openreview.net/pdf?id={m.group(1)}'
    return u if (u.endswith('.pdf') or '/pdf' in u) else None


def page1_text(content):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(content); f.flush()
        return subprocess.run(['pdftotext', '-l', '1', f.name, '-'], capture_output=True, text=True, timeout=120).stdout


def candidates(school, skip_have=True):
    pis = read(HERE / 'hierarchy' / school / 'pis.json')
    own = HERE / 'hierarchy' / school / 'raw/dblp_pubs.json.gz'
    pubs = read(own if own.exists() else HERE.parent / DBLP[school] / 'raw/dblp_pubs.json.gz')['pubs']
    rows = [json.loads(l) for l in gzip.open(HERE / 'hierarchy' / school / 'lab_papers.jsonl.gz', 'rt')]
    have = collections.defaultdict(set)
    for r in rows:
        have[r['pi']].add(norm_title(r.get('title'))); have[r['pi']].add(ndoi(r.get('doi')))
    owner = collections.defaultdict(list)
    for p in pis:
        for q in p.get('dblp') or []:
            owner[q].append(p)
    corr = collections.defaultdict(dict)  # (pid, title) -> arXiv id of the CoRR twin
    for k, rec in pubs.items():
        m = re.search(r'journals/corr/abs-(\d{4})-(\d{4,5})', k)
        if m:
            for q in rec.get('authors') or {}:
                corr[q][norm_title((rec.get('title') or '').rstrip('.'))] = f'{m.group(1)}.{m.group(2)}'
    out = []
    for k, rec in pubs.items():
        y = rec.get('year')
        if not y or not (2016 <= int(y) <= 2026) or 'journals/corr' in k:
            continue
        for q in rec.get('authors') or {}:
            for p in owner.get(q, []):
                years = {l['year'] for l in p['listings']}
                if int(y) not in years and not any((x['start'] or '9999')[:4] < str(y) < (x['end'] or '9999')[:4] for x in p['periods']):
                    continue
                t = norm_title((rec.get('title') or '').rstrip('.'))
                if skip_have and (t in have[p['pi']] or (rec.get('doi') and ndoi(rec['doi']) in have[p['pi']])):
                    continue
                ax = corr[q].get(t) or next((re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', e).group(1) for e in rec.get('ee') or [] if re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', e)), None)
                out.append(dict(pi=p['pi'], names=p['names'], dblp_key=k, title=rec.get('title'), year=int(y), doi=ndoi(rec.get('doi')) or None,
                                venue=rec.get('venue'), byline=list((rec.get('authors') or {}).values()), arxiv=ax, ee=rec.get('ee') or []))
    return out


def db(school):
    c = sqlite3.connect(HERE / 'hierarchy' / school / 'dblp-recover.sqlite', timeout=60, check_same_thread=False)
    c.execute('create table if not exists tries (pi text, dblp_key text, step text, url text, status text, pdf_sha256 text, page1 blob, '
              'accepted int, evidence text, at text, primary key (pi, dblp_key, step))')
    return c


def run(school, workers):
    key = os.environ.get('OPENALEX_API_KEY'); inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    c = db(school); done = {(r[0], r[1]) for r in c.execute('select pi, dblp_key from tries where accepted is not null')}
    todo = [x for x in candidates(school) if (x['pi'], x['dblp_key']) not in done]
    print(json.dumps(dict(school=school, candidates=len(todo))), flush=True)
    wlock = threading.Lock(); acc = collections.Counter()

    def record(x, step, url, status, sha=None, txt=None, ok=0, ev=None):
        with wlock:
            c.execute('insert or replace into tries values (?,?,?,?,?,?,?,?,?,?)', (x['pi'], x['dblp_key'], step, url, status, sha,
                      zlib.compress(txt.encode()) if txt else None, ok, json.dumps(ev) if ev else None, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
            c.commit()

    def one(x):
        nm = Name(x['names']); names = sorted({(given(t[0]), t[-1]) for n in x['names'] for t in [toks(n)] if len(t) >= 2})
        if x['doi'] and key:  # 1. OpenAlex by DOI
            try:
                r = requests.get(f"https://api.openalex.org/works/doi:{x['doi']}", params={'api_key': key, 'select': 'id,authorships,locations,primary_location'}, timeout=60)
                w = r.json() if r.status_code == 200 else None
            except (requests.RequestException, ValueError):
                w = None
            if w:
                a = next((a for a in w.get('authorships') or [] if nm.match(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')), None)
                if a is not None:
                    via = [i.get('display_name') for i in a.get('institutions') or [] if inst == i.get('id') or inst in (i.get('lineage') or [])] + \
                          ['text: ' + z for z in a.get('raw_affiliation_strings') or [] if aff.search(z)]
                    if via:
                        record(x, 'openalex_doi', w['id'], 'ok', ok=1, ev=dict(basis='openalex_authorship', oa=w['id'], school_via=via[:3])); return 'openalex'
                    if a.get('institutions'):
                        record(x, 'openalex_doi', w['id'], 'other_institution', ok=0); return 'other_institution'
                for loc in [w.get('primary_location') or {}] + list(w.get('locations') or []):
                    m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', (loc.get('landing_page_url') or '') + ' ' + (loc.get('pdf_url') or ''))
                    if m and not x['arxiv']:
                        x['arxiv'] = m.group(1)
                    if loc.get('pdf_url') and any(h in loc['pdf_url'] for h in OPEN_HOSTS):
                        x['ee'] = list(x['ee']) + [loc['pdf_url']]
        if x['arxiv']:  # 2. arXiv v1 from the public bulk copy
            url = f"https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{x['arxiv'].split('.')[0]}/{x['arxiv']}v1.pdf"
            try:
                r = requests.get(url, headers={'User-Agent': UA}, timeout=120)
            except requests.RequestException:
                r = None
            if r is not None and r.status_code == 200 and r.content.startswith(b'%PDF'):
                txt = page1_text(r.content); how, quotes = tie(re.sub(r'\s+', ' ', txt), names, aff)
                record(x, 'arxiv', url, 'ok', hashlib.sha256(r.content).hexdigest(), txt, int(bool(how)),
                       dict(basis='page1_arxiv', how=how, quotes=quotes, url=url, pdf_sha256=hashlib.sha256(r.content).hexdigest(), arxiv=x['arxiv']) if how else None)
                if how:
                    return 'arxiv'
        for e in x['ee']:  # 3. an open proceedings PDF
            u = pdf_url(e) if any(h in e for h in OPEN_HOSTS) else None
            if not u:
                continue
            r = polite_get(u)
            if r is not None and r.status_code == 200 and r.content[:4] == b'%PDF':
                txt = page1_text(r.content); how, quotes = tie(re.sub(r'\s+', ' ', txt), names, aff)
                record(x, 'open:' + urlsplit(u).netloc, u, 'ok', hashlib.sha256(r.content).hexdigest(), txt, int(bool(how)),
                       dict(basis='page1_open', how=how, quotes=quotes, url=u, pdf_sha256=hashlib.sha256(r.content).hexdigest()) if how else None)
                if how:
                    return 'open'
        record(x, 'none', None, 'not_recovered', ok=0)
        return 'none'

    with ThreadPoolExecutor(workers) as ex:
        for k, res in enumerate(ex.map(one, todo)):
            acc[res] += 1
            if k % 200 == 0:
                print(json.dumps(dict(school=school, done=k, **acc)), flush=True)
    # accepted rows -> jsonl
    write_accepted(school, c)
    print(json.dumps(dict(school=school, final=dict(acc), accepted_total=c.execute('select count(*) from tries where accepted=1').fetchone()[0])))


def write_accepted(school, c=None):
    """Every accepted paper of every run (not only this run's candidates: earlier recoveries are lab papers by now)."""
    c = c or db(school)
    by = {(x['pi'], x['dblp_key']): x for x in candidates(school, skip_have=False)}
    with gzip.open(HERE / 'hierarchy' / school / 'dblp-recovered.jsonl.gz', 'wt') as f:
        for pi, k, ev in c.execute('select pi, dblp_key, evidence from tries where accepted=1'):
            x = by.get((pi, k))
            if x:
                f.write(json.dumps(dict({kk: x[kk] for kk in ('pi', 'dblp_key', 'title', 'year', 'doi', 'venue', 'byline', 'arxiv')}, evidence=json.loads(ev)), ensure_ascii=False) + '\n')


if __name__ == '__main__':
    if sys.argv[1] == 'write':
        for s_ in sys.argv[2:]:
            write_accepted(s_); print(json.dumps(dict(school=s_, rewritten=True)))
    else:
        run(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
