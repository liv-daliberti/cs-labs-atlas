"""Open full texts of a stratified sample of cited works, for scoring with the passage detector (detector_v2).

frame    every cited OpenAlex work (works_oa.parquet) that is NOT itself a lab paper of the corpus (those already have
         paragraph scores), with stratum = cited year {2016-2021 calibration, 2023, 2024, 2025, 2026} x class
         {published, preprint} (build.py's pubclass; 'other' joins published) and ncite = number of citing lab papers
         (OpenAlex reference lists, >= 5 references).
order    within a stratum, probability-proportional-to-ncite order (Efraimidis-Spirakis keys u^(1/ncite), SEED), so the
         first n texts obtained are a citation-weighted sample: their plain mean estimates the share of CITATIONS going
         to flagged works, and works nobody else cites are not over-represented.
sources  (the fulltext-push rules; no paywalls, logins or bot challenges, never arxiv.org)
           arxiv  an arXiv id (10.48550 DOI or an arXiv location) -> v1 from arXiv's bulk copy
                  storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/<yymm>/<id>v1.pdf. v1 = the text as first
                  posted: for a published work it is the preprint, not the version of record (recorded as 'version').
           pmc    a PubMed Central id in a location -> PMC open data on S3 (pmc-oa-opendata.s3.amazonaws.com), latest
                  version, XML preferred (JATS body), else PDF
           oa_pdf an open location's pdf_url (is_oa, or any repository's) on a host the collectors may use
                  (s2_key_lookup.ok_pdf and core_search.usable), robots.txt honoured, one request per host per 2 s;
                  a response that is not a PDF (an HTML page, a challenge) is a failure
         tried in that order; the first that yields a usable text wins.
extract  claude-homogenization-20261019/tools/fulltext_store.extract (pdftotext, 60 pages; body from the Introduction to
         the last References heading; flags.title_found = OpenAlex title on page 1, the identity check that
         diversity/common.usable_text applies to PDFs)
store    /n/fs/resemble/cs-atlas-cache/citations/ft.sqlite
           texts(key, school, path, kind, chars, intro, body, flags)  = ai-writing/fulltext.sqlite's schema; key = W id,
                                                                        school = 'cited', path = the URL
           meta(key, stratum, source, version, detail, ncite, order_rank, status, at)  every attempt (status ok / fail reason)
         PDFs live only in node-local scratch while being extracted, then are deleted.
target   TARGET usable texts per stratum (attempts stop there), MAX_TRY attempts per stratum at most.
usage: ftsample.py plan | fetch [--workers 8] | status
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import argparse, json, os, re, sqlite3, sys, threading, time, zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from urllib import robotparser

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
DATA = HERE / 'data'
CACHE = P.CACHE / 'citations'
FTDB = Path(os.environ.get('CIT_FTDB', CACHE / 'ft.sqlite'))
SCR = Path(os.environ.get('CIT_SCRATCH', '/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad/ftpdf'))
HOM = P.vendor('homogenization_tools')  # vendored code (tools/vendor_sync.py)
CMU_TOOLS = P.vendor('cmu_tools')
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
SEED, TARGET, MAX_TRY = 20261022, int(os.environ.get('CIT_TARGET', 2500)), int(os.environ.get('CIT_MAXTRY', 9000))
STRATA_YEARS = {'2016-2021': range(2016, 2022), '2023': [2023], '2024': [2024], '2025': [2025], '2026': [2026]}
ARXIV_LOC = re.compile(r'arxiv\.org[:/](?:abs/|pdf/)?(\d{4}\.\d{4,5})', re.I)
PMC_LINK = re.compile(r'(?:ncbi\.nlm\.nih\.gov/pmc/articles|pmc\.ncbi\.nlm\.nih\.gov/articles|europepmc\.org/articles)/(?:PMC)?(\d+)', re.I)
S3 = 'https://pmc-oa-opendata.s3.amazonaws.com'


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def db():
    c = sqlite3.connect(FTDB, timeout=600, check_same_thread=False)
    c.execute('create table if not exists texts (key text primary key, school text, path text, kind text, chars int, intro blob, body blob, flags text)')
    c.execute('create table if not exists frame (key text primary key, stratum text, ncite int, rank int, title text, arxiv text, pmcid text, pdfs text, '
              'pubclass text, field text, cbc int, year int)')
    c.execute('create table if not exists meta (key text primary key, stratum text, source text, version text, detail text, status text, at real)')
    return c


def lab_wids():
    """OpenAlex W ids (and DOIs) of the corpus's lab papers that have paragraph scores."""
    import gzip
    sc = {json.loads(l)['key'] for l in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt')}
    w, d = {}, {}
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        oa = p.get('oa') or ''
        if oa.startswith('https://openalex.org/W'):
            w[int(oa.rsplit('/W', 1)[1])] = p['key']
        if p.get('doi'):
            d[p['doi'].lower().replace('https://doi.org/', '')] = p['key']
    return w, d, sc


def plan():
    import numpy as np, pandas as pd
    W = pd.read_parquet(DATA / 'works_oa.parquet')
    E = pd.read_parquet(DATA / 'edges_oa.parquet')
    C = pd.read_parquet(DATA / 'citing.parquet')
    nref = E.groupby('ci').size()
    ok = set(nref[nref >= 5].index)
    nc = E[E.ci.isin(ok)].wid.value_counts()
    W['ncite'] = W.wid.map(nc).fillna(0).astype(int)
    lw, ld, _ = lab_wids()
    W['is_lab'] = W.wid.isin(set(lw))
    W['cls'] = np.where(W.pubclass == 'preprint', 'preprint', 'published')
    # sources need the raw locations: read them from the OpenAlex cache for the candidate works only
    rows = []
    for s, ys in STRATA_YEARS.items():
        m = W.year.isin(list(ys)) & ~W.is_lab & (W.ncite > 0)
        for cls in ('published', 'preprint'):
            rows.append(W[m & (W.cls == cls)].assign(stratum=f'{s}|{cls}'))
    F = pd.concat(rows)
    rng = np.random.default_rng(SEED)
    F['k'] = np.log(rng.random(len(F))) / F.ncite.values  # Efraimidis-Spirakis: larger is earlier
    F = F.sort_values(['stratum', 'k'], ascending=[True, False])
    F['rank'] = F.groupby('stratum').cumcount()
    want = set(F.wid)
    oa = sqlite3.connect(f'file:{CACHE / "openalex.sqlite"}?mode=ro', uri=True, timeout=600)
    import ftsample_hosts as H
    src = {}
    for wid, b in oa.execute('select wid, data from works where status > 0'):
        i = int(wid[1:])
        if i not in want:
            continue
        w = json.loads(zlib.decompress(b))
        d = (w.get('doi') or '').lower()
        arx = d.split('10.48550/arxiv.', 1)[1] if '10.48550/arxiv.' in d else None
        pmc, pdfs = None, []
        for loc in w.get('locations') or []:
            u = ' '.join(x or '' for x in (loc.get('id'), loc.get('landing_page_url'), loc.get('pdf_url')))
            m = ARXIV_LOC.search(u)
            if m:
                arx = arx or re.sub(r'v\d+$', '', m.group(1)); continue
            m = PMC_LINK.search(u)
            if m:
                pmc = pmc or m.group(1); continue
            pdf = loc.get('pdf_url') or ''
            repo = (loc.get('source') or {}).get('type') == 'repository'
            if pdf and (loc.get('is_oa') or repo) and H.allowed(pdf):
                pdfs.append([pdf, loc.get('version')])
        src[i] = (w.get('display_name') or '', arx, pmc, json.dumps(pdfs))
    c = db()
    c.execute('delete from frame')
    c.executemany('insert into frame values (?,?,?,?,?,?,?,?,?,?,?,?)',
                  [(f'W{r.wid}', r.stratum, int(r.ncite), int(r.rank), *src.get(r.wid, ('', None, None, '[]')), r.pubclass, r.field, int(r.cbc), int(r.year))
                   for r in F.itertuples()])
    c.commit()
    S = pd.read_sql('select stratum, count(*) n, sum(ncite) cites, sum(arxiv is not null) arxiv, sum(pmcid is not null) pmc, '
                    "sum(pdfs != '[]') oapdf, sum(arxiv is not null or pmcid is not null or pdfs != '[]') any_source from frame group by stratum", c)
    lab = W[W.is_lab]
    log(frame=S.to_dict('records'), lab_citables=int(len(lab)), lab_citations=int(lab.ncite.sum()))
    S.to_csv(HERE / 'results' / 'ft_frame.csv', index=False)


class Hosts:
    """robots.txt per host (cached) and a 2-second spacing per host."""

    def __init__(self, s):
        self.s, self.rp, self.last, self.lock = s, {}, defaultdict(float), threading.Lock()

    def can(self, url):
        h = urlsplit(url).scheme + '://' + urlsplit(url).netloc
        with self.lock:
            rp = self.rp.get(h)
        if rp is None:
            rp = robotparser.RobotFileParser()
            try:
                r = self.s.get(h + '/robots.txt', timeout=20)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                if r.status_code in (401, 403):
                    rp.disallow_all = True
            except Exception:
                rp.parse([])
            with self.lock:
                self.rp[h] = rp
        return rp.can_fetch(UA, url)

    def wait(self, url):
        h = urlsplit(url).netloc
        while True:
            with self.lock:
                t = self.last[h] + 2.0 - time.time()
                if t <= 0:
                    self.last[h] = time.time(); return
            time.sleep(t)


def get_pdf(s, url, dst):
    r = s.get(url, timeout=(20, 120), stream=True, allow_redirects=True)
    if r.status_code != 200:
        return f'http_{r.status_code}'
    head = next(r.iter_content(1024), b'')
    if not head.startswith(b'%PDF'):
        return 'not_pdf'
    with open(dst, 'wb') as f:
        f.write(head)
        for ch in r.iter_content(1 << 20):
            f.write(ch)
            if f.tell() > 60 << 20:
                return 'too_big'
    return None


def fetch(workers):
    import requests
    sys.path.insert(0, str(HOM))
    import fulltext_store as fs
    SCR.mkdir(parents=True, exist_ok=True)
    c = db()
    done = {k: st for k, st in c.execute('select key, status from meta')}
    ok = Counter(s for s, st in c.execute('select stratum, status from meta') if st == 'ok')
    tried = Counter(s for s, in c.execute('select stratum from meta'))
    F = defaultdict(list)
    for r in c.execute('select key, stratum, rank, title, arxiv, pmcid, pdfs from frame order by stratum, rank'):
        if r[0] not in done and (r[4] or r[5] or r[6] != '[]'):
            F[r[1]].append(r)
    # interleave strata so every stratum progresses
    queue = []
    its = {k: iter(v) for k, v in F.items()}
    while its:
        for k in list(its):
            x = next(its[k], None)
            if x is None:
                del its[k]
            else:
                queue.append(x)
    log(queue=len(queue), ok=dict(ok), tried=dict(tried))
    local = threading.local(); wl = threading.Lock()
    hosts = Hosts(requests.Session())

    def sess():
        if not hasattr(local, 's'):
            local.s = requests.Session(); local.s.headers['User-Agent'] = UA
        return local.s

    def one(r):
        key, stratum, rank, title, arx, pmc, pdfs = r
        with wl:
            if ok[stratum] >= TARGET or tried[stratum] >= MAX_TRY:
                return
            tried[stratum] += 1
        s = sess(); dst = SCR / f'{key}.pdf'
        tries = []
        if arx and re.match(r'^\d{4}\.\d{4,5}$', arx):
            tries.append(('arxiv', f'https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{arx[:4]}/{arx}v1.pdf', 'arXiv v1', arx))
        if pmc:
            tries.append(('pmc', None, None, pmc))
        for u, v in json.loads(pdfs):
            if 'arxiv.org' not in u:
                tries.append(('oa_pdf', u, v, urlsplit(u).netloc))
        status, row = 'no_source', None
        for src, url, ver, detail in tries:
            try:
                kind = 'pdf'
                if src == 'pmc':
                    time.sleep(0.5)
                    rr = s.get(f'{S3}/?list-type=2&prefix=PMC{pmc}.', timeout=60)
                    keys = re.findall(r'<Key>([^<]+)</Key>', rr.text) if rr.status_code == 200 else []
                    vv = max((int(x.group(1)) for k in keys if (x := re.search(r'\.(\d+)/', k))), default=None)
                    if not vv:
                        status = 'pmc_not_open'; continue
                    xk, pk = f'PMC{pmc}.{vv}/PMC{pmc}.{vv}.xml', f'PMC{pmc}.{vv}/PMC{pmc}.{vv}.pdf'
                    if xk in keys:
                        url, kind, ver = f'{S3}/{xk}', 'xml', f'PMC v{vv} (xml)'
                        rr = s.get(url, timeout=120)
                        if rr.status_code != 200:
                            status = f'http_{rr.status_code}'; continue
                        dst = SCR / f'{key}.xml'; dst.write_bytes(rr.content); err = None
                    elif pk in keys:
                        url, ver = f'{S3}/{pk}', f'PMC v{vv} (pdf)'
                        err = get_pdf(s, url, dst)
                    else:
                        status = 'pmc_no_file'; continue
                elif src == 'oa_pdf':
                    if not hosts.can(url):
                        status = 'robots'; continue
                    hosts.wait(url)
                    err = get_pdf(s, url, dst)
                else:
                    err = get_pdf(s, url, dst)
                if err:
                    status = f'{src}:{err}'; continue
                _, _, sx, flags = fs.extract((str(dst), kind, title))
                dst.unlink(missing_ok=True)
                if not sx:
                    status = f'{src}:extract_{flags.get("error")}'; continue
                body = sx.get('body') or ''
                usable = len(body.split()) >= 1000 and (kind != 'pdf' or bool(flags.get('title_found')))
                if not usable:
                    status = f'{src}:unusable'
                    continue
                row = (key, 'cited', url, kind, len(body), zlib.compress((sx.get('intro') or '').encode()), zlib.compress(body.encode()),
                       json.dumps(dict(flags, source=src, version=ver)))
                status = 'ok'
                break
            except Exception as e:
                status = f'{src}:{type(e).__name__}'
            finally:
                for p in (SCR / f'{key}.pdf', SCR / f'{key}.xml'):
                    p.unlink(missing_ok=True)
        with wl:
            if row:
                c.execute('insert or replace into texts values (?,?,?,?,?,?,?,?)', row); ok[stratum] += 1
            c.execute('insert or replace into meta values (?,?,?,?,?,?,?)', (key, stratum, (row and json.loads(row[7])['source']), (row and json.loads(row[7])['version']),
                                                                           None, status, time.time()))
            n = sum(tried.values())
            if n % 100 == 0:
                c.commit()
                log(tried=dict(tried), ok=dict(ok))

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, queue))
    c.commit()
    log(final_tried=dict(tried), final_ok=dict(ok))


def status():
    c = db()
    for r in c.execute('select stratum, status, count(*) from meta group by stratum, status order by stratum, count(*) desc'):
        print(r)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    sys.path.insert(0, str(HERE))
    {'plan': plan, 'fetch': lambda: fetch(a.workers), 'status': status}[a.cmd]()
