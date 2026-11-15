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
usage: [DBLP_RECOVER_YEARS=2016-2023] dblp_recover.py <school> [--workers 6] | dblp_recover.py write <school> ...
"""
import collections, gzip, hashlib, json, os, re, sqlite3, subprocess, sys, tempfile, threading, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
import requests

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import read, DBLP, INST, AFF, ndoi, norm_title, Name, toks, given  # noqa: E402
from pi_fulltext_affiliation import tie  # noqa: E402
import atlas_paths as P  # noqa: E402  (every path in one place)
from pihier.common import school_scope_work  # noqa: E402
from pihier.names import name_toks  # noqa: E402
from pihier.papers import _authorship_school_via  # noqa: E402

UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
OPEN_HOSTS = ('ceur-ws.org', 'aclanthology.org', 'proceedings.mlr.press', 'openaccess.thecvf.com', 'papers.nips.cc', 'proceedings.neurips.cc',
              'bmva-archive.org.uk', 'www.ieee-security.org', 'openproceedings.org',
              'www.usenix.org', 'usenix.org', 'www.ijcai.org', 'ojs.aaai.org', 'openreview.net', 'www.isca-speech.org',
              'www.roboticsproceedings.org', 'roboticsproceedings.org', 'jmlr.org', 'www.jmlr.org', 'dl.acm.org/doi/pdf')
_last = collections.defaultdict(float); _lock = threading.Lock(); _robots = {}


_HT = []


def _throttle():
    """fulltext-push/host_throttle.py (shared pacing state in the collectors' raw directory), loaded by path; None when it is not there."""
    if not _HT:
        import importlib.util
        f = Path(P.FULLTEXT_PUSH) / 'host_throttle.py'
        mod = None
        if f.exists():
            spec = importlib.util.spec_from_file_location('host_throttle', f); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        _HT.append(mod)
    return _HT[0]


CRAWL_DELAY = {'www.usenix.org': 10.0}   # robots.txt Crawl-delay of the hosts that state one


def polite_get(url, delay=3.0):
    host = urlsplit(url).netloc
    delay = max(delay, CRAWL_DELAY.get(host, 0))
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
    ht = _throttle()
    if ht is not None:   # R-PAP-36: one request budget per host for every client (the download loops and parallel recovery jobs): host_throttle's slots and 429 cooldowns
        if ht.cooldown_left(host) > ht.WAIT_MAX:
            return None
        wait = ht.reserve(host, delay)
    else:
        with _lock:
            wait = _last[host] + delay - time.time(); _last[host] = max(time.time(), _last[host] + delay)
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=90)
    except requests.RequestException:
        return None
    if r.status_code == 429 and ht is not None:
        ht.record_429(host)
    return r


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
    # IACR ePrint is not asked: eprint.iacr.org answers automated clients with a Cloudflare challenge and its robots.txt states an AI policy against
    # using the PDFs (R-PAP-36, 2026-11-05: Devadas's 2021 ePrint paper stays `dblp_unconfirmed`)
    m = re.match(r'https://www\.usenix\.org/conference/([a-z]+)(\d{2})/presentation/([\w\-]+)/?$', u)   # R-PAP-36: USENIX presentation page -> its open PDF
    if m:
        return f'https://www.usenix.org/system/files/{m.group(1)}{m.group(2)}-{m.group(3)}.pdf'
    m = re.match(r'https://(?:www\.)?jmlr\.org/papers/v(\d+)/([\w\-.]+?)\.html$', u)   # R-PAP-36: JMLR volume page -> its PDF
    if m:
        return f'https://jmlr.org/papers/volume{m.group(1)}/{m.group(2)}/{m.group(2)}.pdf'
    m = re.match(r'https://openreview\.net/forum\?id=([\w\-]+)', u)
    if m:
        return f'https://openreview.net/pdf?id={m.group(1)}'
    return u if (u.endswith('.pdf') or '/pdf' in u) else None


def page1_text(content):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(content); f.flush()
        return subprocess.run(['pdftotext', '-l', '1', f.name, '-'], capture_output=True, text=True, timeout=120).stdout


# DBLP_RECOVER_YEARS=A-B limits a run to publication years A..B (e.g. the part of the window the school's OpenAlex sweep
# already covers); write_accepted reads every accepted row whatever the limit.
Y0, Y1 = (int(v) for v in (os.environ.get('DBLP_RECOVER_YEARS') or '2016-2026').split('-'))


def dump_pubs(pis, school=None):
    """The PIs' DBLP records from DBLP's own dump (hierarchy/dblp-dump-persons.json.gz, tools/dblp_dump_persons.py) in the
    cached-list shape {key: {title, year, doi, venue, ee, authors: {pid or 'n<i>': name}}}; the PI's own byline entry is
    keyed by the PI's pid."""
    persons = dict(read(P.data('dblp-dump-persons.json.gz')).get('persons') or {})
    own = P.data('dblp-dump-persons-school.json.gz', school) if school else None
    if own is not None and own.exists():   # an onboarding school's own persons (dblp_dump_persons.py <key>): the shared file holds the pre-protocol schools only
        persons.update(read(own).get('persons') or {})
    out = {}
    for p in pis:
        for q in p.get('dblp') or []:
            per = persons.get(q) or {}
            mine = {re.sub(r'\s+\d{4}$', '', n) for n in per.get('names') or []}
            for rec in per.get('pubs') or []:
                r = out.setdefault(rec['key'], dict(title=rec.get('title'), year=rec.get('year'), doi=(rec.get('dois') or [None])[0],
                                                    venue=rec.get('venue'), ee=[], authors={}))
                for i, (nm, pid) in enumerate(rec.get('authors') or []):
                    k = q if re.sub(r'\s+\d{4}$', '', nm) in mine else (pid or f'n{i}')
                    r['authors'].setdefault(k, re.sub(r'\s+\d{4}$', '', nm))
    return out


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def bare_key(k):
    """'https://dblp.org/rec/conf/colt/FreundLW22' and 'conf/colt/FreundLW22' are one record."""
    return re.sub(r'^https?://dblp\.org/rec/', '', str(k or ''))


def page1_name_forms(names):
    """Keep both a literal byline first name and its nickname expansion for page-one matching."""
    return sorted({(first, t[-1]) for n in names for t in [name_toks(n)] if len(t) >= 2
                   for first in (given(t[0]), t[0].lower())})


_EE_CACHE = {}


def dump_ee(keys):
    """{bare key: [ee URLs]} of the given records from DBLP's own dump XML (never dblp.org: a challenge page answers there)."""
    from dblp_dump_pages import records
    import html as html_
    want = {bare_key(k) for k in keys}
    if want <= set(_EE_CACHE):
        return {k: _EE_CACHE[k] for k in want}
    for key, body in records(P.DBLP_DUMP_XML):
        if key in want:
            _EE_CACHE[key] = [re.sub(r'\s+', '', html_.unescape(m)) for m in re.findall(r'<ee[^>]*>([^<]*)</ee>', body)]
    for k in want - set(_EE_CACHE):
        _EE_CACHE[k] = []
    return {k: _EE_CACHE[k] for k in want}


def candidates(school, skip_have=True):
    only_keys = {k.strip() for k in os.environ.get('DBLP_RECOVER_KEYS', '').split(',') if k.strip()}
    pis = read(P.data('pis.json', school))
    own = P.data('dblp_pubs.json.gz', school)
    legacy = {}
    if own.exists() or school in DBLP:
        legacy = read(own if own.exists() else P.archive_sweep(DBLP[school]) / 'raw/dblp_pubs.json.gz')['pubs']
    # R-PAP-36 (2026-11-05): the cached lists hold only what the census queries returned (MIT's Mossel NeurIPS 2022 and Freund COLT 2022 were never
    # candidates); the PI's full DBLP person page from the dump adds every record the lists lack. A pre-protocol school keeps its cached records
    # (they carry `ee`); a record only the dump has gets its `ee` from the dump XML (`dump_ee`).
    pubs = dict(legacy)
    bare_have = {bare_key(k) for k in legacy}
    for k, rec in dump_pubs(pis, school).items():
        if bare_key(k) not in bare_have:
            pubs[k] = rec
    rows = [json.loads(l) for l in gzip.open(P.data('lab_papers.jsonl.gz', school), 'rt')]
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
    need_ee = [k for k, rec in pubs.items() if not rec.get('ee') and rec.get('year') and 2016 <= int(rec['year']) <= 2026 and 'journals/corr' not in k and Y0 <= int(rec['year']) <= Y1 and (not only_keys or any(bare_key(k).endswith('/' + key) for key in only_keys))]
    ee_of = dump_ee(need_ee) if need_ee and os.environ.get('DBLP_RECOVER_NO_EE') != '1' else {}
    for k, rec in pubs.items():
        if only_keys and not any(bare_key(k).endswith('/' + key) for key in only_keys):
            continue
        if not rec.get('ee') and bare_key(k) in ee_of:
            rec['ee'] = ee_of[bare_key(k)]
        y = rec.get('year')
        if not y or not (2016 <= int(y) <= 2026) or 'journals/corr' in k or not (Y0 <= int(y) <= Y1):
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
                                venue=rec.get('venue'), byline=list(dict.fromkeys((rec.get('authors') or {}).values())), arxiv=ax, ee=rec.get('ee') or []))
    return out


def db(school):
    c = sqlite3.connect(P.data_w('dblp-recover.sqlite', school), timeout=60, check_same_thread=False)
    c.execute('create table if not exists tries (pi text, dblp_key text, step text, url text, status text, pdf_sha256 text, page1 blob, '
              'accepted int, evidence text, at text, primary key (pi, dblp_key, step))')
    return c


def run(school, workers):
    key = os.environ.get('OPENALEX_API_KEY'); inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    c = db(school)
    retry = '--retry' in sys.argv   # R-PAP-36: ask again for the records an earlier run could not confirm (new hosts, a fuller candidate list)
    # a record is done when it was accepted or OpenAlex puts the PI at another institution; --retry asks again for every other (earlier hosts failed or were missing)
    done = {(r[0], r[1]) for r in c.execute('select pi, dblp_key, status, accepted from tries where accepted is not null') if r[3] == 1 or r[2] == 'other_institution' or not retry}
    # a chain of jobs (59 minutes each) shares one retry: a record asked again since DBLP_RETRY_SINCE (an ISO time, set once for the chain) is done
    since = os.environ.get('DBLP_RETRY_SINCE')
    if retry and since:
        done |= {(r[0], r[1]) for r in c.execute('select pi, dblp_key from tries where at >= ?', (since,))}
    todo = [x for x in candidates(school) if (x['pi'], x['dblp_key']) not in done]
    only_keys = {k.strip() for k in os.environ.get('DBLP_RECOVER_KEYS', '').split(',') if k.strip()}
    if only_keys:
        todo = [x for x in todo if any(x['dblp_key'].endswith('/' + key) for key in only_keys)]
    pdf_overrides = json.loads(os.environ.get('DBLP_RECOVER_PDF_OVERRIDES', '{}'))
    for x in todo:
        url = pdf_overrides.get(bare_key(x['dblp_key']))
        if url:
            x['ee'] = list(dict.fromkeys([*x['ee'], url]))
    print(json.dumps(dict(school=school, candidates=len(todo))), flush=True)
    wlock = threading.Lock(); acc = collections.Counter()

    def record(x, step, url, status, sha=None, txt=None, ok=0, ev=None):
        with wlock:
            c.execute('insert or replace into tries values (?,?,?,?,?,?,?,?,?,?)', (x['pi'], x['dblp_key'], step, url, status, sha,
                      zlib.compress(txt.encode()) if txt else None, ok, json.dumps(ev) if ev else None, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())))
            c.commit()

    def one(x):
        read_pages = []
        nm = Name(x['names']); names = page1_name_forms(x['names'])
        if x['doi']:  # 1. OpenAlex by DOI; public singleton lookup also works without a key
            try:
                params = {'select': 'id,authorships,locations,primary_location'}
                if key:
                    params['api_key'] = key
                r = requests.get(f"https://api.openalex.org/works/doi:{x['doi']}", params=params, timeout=60)
                w = r.json() if r.status_code == 200 else None
            except (requests.RequestException, ValueError):
                w = None
            if w:
                source_work = w
                w = school_scope_work(w, school)
                a = next((a for a in w.get('authorships') or [] if nm.match(a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')), None)
                if a is not None:
                    via = _authorship_school_via(w, a, inst, aff, school=school)
                    if via:
                        record(x, 'openalex_doi', w['id'], 'ok', ok=1, ev=dict(basis='openalex_authorship', oa=w['id'], school_via=via[:3], openalex_work=source_work)); return 'openalex'
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
                txt = page1_text(r.content); how, quotes = tie(re.sub(r'\s+', ' ', txt), names, aff); read_pages.append(url)
                record(x, 'arxiv', url, 'ok', hashlib.sha256(r.content).hexdigest(), txt, int(bool(how)),
                       dict(basis='page1_arxiv', how=how, quotes=quotes, url=url, pdf_sha256=hashlib.sha256(r.content).hexdigest(), arxiv=x['arxiv'], dblp_key=bare_key(x['dblp_key']), fetched_at=now()) if how else None)
                if how:
                    return 'arxiv'
        for e in x['ee']:  # 3. an open proceedings PDF
            u = pdf_url(e) if any(h in e for h in OPEN_HOSTS) else None
            if not u:
                continue
            r = polite_get(u)
            if r is not None and r.status_code == 200 and r.content[:4] == b'%PDF':
                txt = page1_text(r.content); how, quotes = tie(re.sub(r'\s+', ' ', txt), names, aff); read_pages.append(u)
                record(x, 'open:' + urlsplit(u).netloc, u, 'ok', hashlib.sha256(r.content).hexdigest(), txt, int(bool(how)),
                       dict(basis='page1_open', how=how, quotes=quotes, url=u, pdf_sha256=hashlib.sha256(r.content).hexdigest(), dblp_key=bare_key(x['dblp_key']), fetched_at=now()) if how else None)
                if how:
                    return 'open'
        # R-PAP-36: no page-1 evidence, so not added; the reason is kept for later (a ledger of what could not be confirmed)
        why = ('page1_read_school_not_named' if read_pages else 'no_open_page1_source' if not x['arxiv'] and not any(h in e for e in x['ee'] for h in OPEN_HOSTS) else 'page1_fetch_failed')
        record(x, 'none', None, 'dblp_unconfirmed', ok=0, ev=dict(reason=why, dblp_key=bare_key(x['dblp_key']), ee=x['ee'][:4]))
        return 'none'

    with ThreadPoolExecutor(workers) as ex:
        for k, res in enumerate(ex.map(one, todo)):
            acc[res] += 1
            if k % 200 == 0:
                print(json.dumps(dict(school=school, done=k, **acc)), flush=True)
    # accepted rows -> jsonl
    only_keys_env = os.environ.pop('DBLP_RECOVER_KEYS', None)
    no_ee_env = os.environ.get('DBLP_RECOVER_NO_EE')
    os.environ['DBLP_RECOVER_NO_EE'] = '1'
    try:
        write_accepted(school, c)
    finally:
        if only_keys_env is not None:
            os.environ['DBLP_RECOVER_KEYS'] = only_keys_env
        if no_ee_env is None:
            os.environ.pop('DBLP_RECOVER_NO_EE', None)
        else:
            os.environ['DBLP_RECOVER_NO_EE'] = no_ee_env
    print(json.dumps(dict(school=school, final=dict(acc), accepted_total=c.execute('select count(*) from tries where accepted=1').fetchone()[0])))


def write_accepted(school, c=None):
    """Every accepted paper of every run (not only this run's candidates: earlier recoveries are lab papers by now)."""
    global Y0, Y1
    c = c or db(school)
    lim, (Y0, Y1) = (Y0, Y1), (2016, 2026)  # every accepted row, whatever DBLP_RECOVER_YEARS limited this run to
    try:
        by = {(x['pi'], x['dblp_key']): x for x in candidates(school, skip_have=False)}
    finally:
        Y0, Y1 = lim
    with gzip.open(P.data_w('dblp-recovered.jsonl.gz', school), 'wt') as f:
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
