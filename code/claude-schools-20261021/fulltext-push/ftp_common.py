"""Shared helpers for the lab-paper full-text push (2026-10-22): lab papers per school, their OpenAlex records, the
catalogs' state read in short rowid chunks, and candidate writes that commit per small batch.

The catalogs (homogenizing-science/data/fulltext/<school>/catalog.sqlite) live on NFS with a rollback journal and are
written by running collectors that wait at most 120 s for a lock: every read here is a short rowid-chunked statement
on a read-only connection, and every write commits per batch of at most BATCH rows (retrying on a lock).
"""
import gzip, json, re, sqlite3, sys, time, unicodedata, zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
SCHOOLS = HERE.parent
FT = Path('/n/fs/similarity/homogenizing-science/data/fulltext')
CMU_TOOLS = Path('/n/fs/similarity/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools')
PRIN_TOOLS = Path('/n/fs/similarity/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools')
for p in (CMU_TOOLS, PRIN_TOOLS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
LOCAL = ('downloaded', 'fulltext_xml')
BATCH = 200
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
SCRATCH = Path('/tmp/claude-363432/-n-fs-similarity-maxent-grpo/2bd068f5-5142-4dac-89d1-67eb470f92c1/scratchpad')


def now():
    return datetime.now(timezone.utc).isoformat()


def nt(t):
    t = re.sub(r'<[^>]+>', ' ', t or '')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def load_env():
    """API keys from the session's scratchpad env files into os.environ (never printed or written)."""
    import os
    for name in ('openalex', 's2', 'core'):
        f = SCRATCH / f'{name}.env'
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.replace('export ', '').strip()
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def oa_short(oa):
    return (oa or '').rsplit('/', 1)[-1]


def oa_work_id(school, r):
    return f"{school}_oa_{oa_short(r['oa'])}"


def lab_papers(school):
    """{paper key: row} (first row per key, as tools/lab_paper_copies.py) with 'pis' = every PI the paper is listed for."""
    out, pis = {}, defaultdict(list)
    for line in gzip.open(SCHOOLS / 'hierarchy' / school / 'lab_papers.jsonl.gz', 'rt'):
        r = json.loads(line)
        k = r['work'] or r['oa']
        out.setdefault(k, r)
        if r['pi'] not in pis[k]:
            pis[k].append(r['pi'])
    for k, r in out.items():
        r['pis'] = pis[k]
    return out


def oa_bodies(school, ids):
    """{OpenAlex id URL: work record} from hierarchy/<school>/pi-works.sqlite (zlib JSON), plus our own cache."""
    want = set(ids)
    out = {}
    db = sqlite3.connect(f"file:{SCHOOLS / 'hierarchy' / school / 'pi-works.sqlite'}?mode=ro", uri=True, timeout=60)
    for i, b in db.execute('SELECT id, body FROM works'):
        if i in want:
            try:
                out[i] = json.loads(zlib.decompress(b))
            except Exception:
                pass
    db.close()
    cache = HERE / 'raw' / 'openalex_works.jsonl'
    if cache.exists():
        for line in cache.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('id') in want and r.get('body') and r['id'] not in out:
                out[r['id']] = r['body']
    return out


def fetch_oa_bodies(ids):
    """OpenAlex single-work records by id for papers whose record is not cached (with the key from the environment)."""
    import os, requests
    load_env()
    cache = HERE / 'raw' / 'openalex_works.jsonl'
    cache.parent.mkdir(exist_ok=True)
    s = requests.Session(); s.headers['User-Agent'] = UA
    key = os.environ.get('OPENALEX_API_KEY')
    got = {}
    with cache.open('a') as f:
        for i in ids:
            time.sleep(0.15)
            try:
                r = s.get('https://api.openalex.org/works/' + oa_short(i),
                          params=dict(select='id,doi,title,publication_year,ids,locations,primary_location', **({'api_key': key} if key else {})),
                          timeout=(15, 60))
            except Exception:
                continue
            if r.status_code == 200:
                got[i] = r.json()
                f.write(json.dumps(dict(id=i, at=now(), body=got[i])) + '\n')
    return got


def chunks(db, table, cols, n=1500):
    hi = db.execute(f'SELECT MAX(rowid) FROM {table}').fetchone()[0] or 0
    for lo in range(0, hi + 1, n):
        yield from db.execute(f'SELECT {cols} FROM {table} WHERE rowid >= ? AND rowid < ?', (lo, lo + n)).fetchall()
        time.sleep(0.05)


def catalog_state(school, with_urls=True):
    """Read-only, rowid-chunked: status {id: st}, doi {doi: id (a local one preferred)}, title {nt: id (local preferred)},
    local keys (ids, 'doi:..', 't:..' with a copy), urls {id: set(candidate and attempted urls)}."""
    path = FT / school / 'catalog.sqlite'
    st, doi, title, local, urls = {}, {}, {}, set(), defaultdict(set)
    if not path.exists():
        return dict(status=st, doi=doi, title=title, local=local, urls=urls)
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    for i, d, s, t in chunks(db, 'works', 'id, doi, status, title'):
        if st.get(i) not in LOCAL:
            st[i] = s
        if d:
            d = ndoi(d)
            if s in LOCAL or d not in doi:
                doi[d] = i
        if t:
            k = nt(t)
            if s in LOCAL or k not in title:
                title[k] = i
        if s in LOCAL:
            local.update(x for x in (i, d and 'doi:' + ndoi(d), t and 't:' + nt(t)) if x)
    if with_urls:
        for tbl in ('candidates', 'attempts'):
            for w, u in chunks(db, tbl, 'work_id, url', n=20000):
                urls[w].add(u)
    db.close()
    return dict(status=st, doi=doi, title=title, local=local, urls=urls)


def match_work(school, r, cs):
    """The catalog work of a lab paper by the counter's rule: collection work id, our OA-keyed id, DOI, arXiv DOI, title."""
    st = cs['status']
    for k in (r.get('work'), oa_work_id(school, r)):
        if k and k in st:
            return k
    d = ndoi(r.get('doi'))
    if d and d in cs['doi']:
        return cs['doi'][d]
    k = nt(r.get('title'))
    if len(k) >= 20 and k in cs['title']:
        return cs['title'][k]
    return None


def is_local(school, r, cs):
    w = match_work(school, r, cs)
    if w and cs['status'].get(w) in LOCAL:
        return True
    d = ndoi(r.get('doi'))
    return bool((d and 'doi:' + d in cs['local']) or ('t:' + nt(r.get('title')) in cs['local']))


def connect_rw(school):
    return sqlite3.connect(str(FT / school / 'catalog.sqlite'), timeout=120)


def write_batches(db, sql, rows, batch=BATCH):
    """executemany in batches, each committed on its own; a lock held by the collector is waited out. -> rows changed."""
    n = 0
    for i in range(0, len(rows), batch):
        part = rows[i:i + batch]
        for attempt in range(30):
            try:
                c = 0
                for r in part:
                    c += db.execute(sql, r).rowcount
                db.commit(); n += c; break
            except sqlite3.OperationalError:
                db.rollback(); time.sleep(20)
        else:
            raise RuntimeError('catalog stayed locked')
        time.sleep(0.2)
    return n


def write_candidates(school, rows, evidence, label):
    """rows: dicts work_id, url, landing_url, version, source, detail -> evidence JSON + INSERT OR IGNORE candidates
    (committed per batch). Returns the number of new candidate rows."""
    rows = list({(r['work_id'], r['url']): r for r in rows}.values())
    if not rows:
        return 0
    evidence.parent.mkdir(parents=True, exist_ok=True)
    # small evidence files: the collector reads a candidate's evidence file (as JSON) once per attempt
    n = 0
    db = connect_rw(school)
    for i in range(0, len(rows), 100):
        part = rows[i:i + 100]
        ev = evidence.with_name(f'{evidence.stem}-{i // 100:04d}.json')
        ev.write_text(json.dumps(dict(rule=label, created_at=now(), rows=part)))
        n += write_batches(db, 'INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',
                           [(r['work_id'], r['url'], r.get('landing_url'), r.get('license'), r.get('version'), str(ev)) for r in part])
    db.close()
    return n


ARXIV_LOC = re.compile(r'arxiv\.org[:/](?:abs/|pdf/)?(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})', re.I)
PMC_LINK = re.compile(r'(?:ncbi\.nlm\.nih\.gov/pmc/articles|pmc\.ncbi\.nlm\.nih\.gov/articles|europepmc\.org/articles)/(?:PMC)?(\d+)', re.I)


def arxiv_of(r, body):
    """An arXiv id for the paper: its 10.48550 DOI, else an arXiv location in its OpenAlex record."""
    d = ndoi(r.get('doi'))
    if d.startswith('10.48550/arxiv.'):
        return d.split('arxiv.', 1)[1]
    for loc in (body or {}).get('locations') or []:
        for v in (loc.get('id'), loc.get('landing_page_url'), loc.get('pdf_url')):
            m = ARXIV_LOC.search(v or '')
            if m:
                return re.sub(r'v\d+$', '', m.group(1))
    return None


def oa_location_rows(work_id, body):
    """Candidate rows from an OpenAlex record's locations (arXiv and PMC excluded: they go through the bulk copies):
    an open location's pdf_url on a host the collectors may use; a repository's pdf_url even when OpenAlex marks it not
    OA (an author-deposited file is served openly or fails); a repository's landing page (the collector follows its
    citation_pdf_url). Returns (rows, pmcids)."""
    import s2_key_lookup as s2k, core_search as cs
    rows, pmc = [], set()
    for loc in (body or {}).get('locations') or []:
        pdf, land = loc.get('pdf_url') or '', loc.get('landing_page_url') or ''
        src = loc.get('source') or {}
        if ARXIV_LOC.search(pdf + ' ' + land + ' ' + (loc.get('id') or '')):
            continue
        m = PMC_LINK.search(pdf + ' ' + land)
        if m:
            pmc.add(m.group(1)); continue
        repo = src.get('type') == 'repository'
        url = None
        if pdf and (loc.get('is_oa') or repo) and s2k.ok_pdf(pdf) and cs.usable(pdf):
            url = pdf
        elif pdf and loc.get('is_oa') and (urlsplit(pdf).hostname or '') == 'link.springer.com' and '/content/pdf/' in pdf:
            url = pdf  # an open-access Springer article's own PDF (robots.txt still decides)
        elif repo and land and s2k.ok_pdf(land) and cs.usable(land):
            url = land
        if url:
            rows.append(dict(work_id=work_id, url=url, landing_url=land or None, version=loc.get('version'), license=loc.get('license'),
                             source='openalex_location', detail=src.get('display_name')))
    return rows, pmc


def pmc_rows(work_id, pmcids, memo, session):
    import s2_key_lookup as s2k
    out = []
    for p in sorted(pmcids):
        for u in s2k.pmc_files(session, p, memo):
            out.append(dict(work_id=work_id, url=u, landing_url=f'https://pmc.ncbi.nlm.nih.gov/articles/PMC{p}/', version=None,
                            source='pmc_open_data', detail=p))
    return out


def bulk_rows(want, source):
    """{work_id: arXiv id} -> candidate rows on arXiv's bulk copy (storage.googleapis.com/arxiv-dataset), never arxiv.org."""
    from arxiv_bulk import listing
    urls = listing(list(dict.fromkeys(want.values())))
    rows, missing = [], 0
    for w, a in want.items():
        if urls.get(a):
            rows.append(dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', version='submittedVersion', source=source, detail=a))
        else:
            missing += 1
    return rows, missing
