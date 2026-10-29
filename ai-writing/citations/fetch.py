"""OpenAlex fetches for the citation analysis, cached in one SQLite file on /n/fs/resemble.

citing  every lab paper with a paragraph score (ai-writing/paragraph_scores.jsonl.gz) that is in papers.jsonl.gz:
        its OpenAlex work by id (filter=openalex:W1|...|W50), or for DBLP-recovered rows (no OpenAlex id) by DOI
        (filter=doi:...|...). Stored: referenced_works, publication_year, type, primary_topic, cited_by_count.
works   every unique work any of them cites: publication_year, type, cited_by_count, primary_topic, primary_location,
        locations, indexed_in, title, abstract_inverted_index.
Ids OpenAlex no longer returns in a list query (deleted or merged) are retried once as singletons (/works/W..., which
follows merges); anything still missing is stored with status 0.

Budget. A list request costs 1 credit and the key has 10,000 credits a day (reset at 00:00 UTC); singletons cost 0. The
same key serves the owner's other collectors, so fetching stops while X-RateLimit-Remaining is below RESERVE and resumes
after the reset. At most ~7 requests per second over all threads; 429 and 5xx back off.

The key is read from ~/.config/cs-atlas/openalex.env and never printed or logged.
usage: fetch.py citing | works [--order priority] | status
"""
import gzip, json, os, sqlite3, sys, threading, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
CACHE = Path('/n/fs/resemble/cs-atlas-cache/citations')
DB = CACHE / 'openalex.sqlite'
RESERVE = int(os.environ.get('CIT_RESERVE', 1200))
RPS = 7.0
CITING_SELECT = 'id,doi,publication_year,type,referenced_works,referenced_works_count,primary_topic,cited_by_count'
WORK_SELECT = ('id,doi,display_name,publication_year,type,cited_by_count,primary_topic,primary_location,locations,indexed_in,'
               'abstract_inverted_index')


def api_key():
    for line in open(os.path.expanduser('~/.config/cs-atlas/openalex.env')):
        line = line.strip()
        if line.startswith('OPENALEX_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    raise SystemExit('no OPENALEX_API_KEY')


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def db():
    CACHE.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=600, check_same_thread=False)
    c.execute('pragma journal_mode=delete')
    c.execute('create table if not exists citing (key text primary key, query text, wid text, status int, data blob, at real)')
    c.execute('create table if not exists works (wid text primary key, status int, data blob, at real)')
    c.execute('create table if not exists requests (t real, stage text, n int, status int, remaining int)')
    return c


class Client:
    """Rate-limited OpenAlex client shared by the worker threads."""

    def __init__(self):
        self.key, self.s = api_key(), threading.local()
        self.lock, self.next_t = threading.Lock(), 0.0
        self.remaining, self.reset = None, None

    def session(self):
        if not hasattr(self.s, 'v'):
            self.s.v = requests.Session()
        return self.s.v

    def wait_slot(self):
        with self.lock:
            now = time.time()
            t = max(now, self.next_t)
            self.next_t = t + 1.0 / RPS
        time.sleep(max(0.0, t - time.time()))

    def wait_budget(self):
        while self.remaining is not None and self.remaining < RESERVE:
            nap = min(1800, max(60, (self.reset or 600) + 120))
            log(budget_pause=self.remaining, sleep=nap)
            time.sleep(nap)
            self.remaining = None  # re-probe after the nap

    def get(self, path, params, list_query=True):
        if list_query:
            self.wait_budget()
        for attempt in range(8):
            self.wait_slot()
            try:
                r = self.session().get('https://api.openalex.org' + path, params=dict(params, api_key=self.key), timeout=180)
            except requests.RequestException as e:
                log(error=type(e).__name__, attempt=attempt); time.sleep(5 * (attempt + 1)); continue
            h = r.headers
            if 'X-RateLimit-Remaining' in h:
                with self.lock:
                    self.remaining = int(h['X-RateLimit-Remaining']); self.reset = int(h.get('X-RateLimit-Reset', 600))
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429 and self.remaining is not None and self.remaining < 5:
                self.wait_budget(); continue
            log(http=r.status_code, attempt=attempt)
            time.sleep(min(300, 5 * 2 ** attempt))
        raise RuntimeError('OpenAlex request kept failing')


def short(w):
    return w.rsplit('/', 1)[-1] if w else w


def citing_targets():
    keys = set()
    for line in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt'):
        keys.add(json.loads(line)['key'])
    out = []
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        if p['key'] not in keys:
            continue
        oa, doi = p.get('oa') or '', (p.get('doi') or '').lower().replace('https://doi.org/', '')
        if oa.startswith('https://openalex.org/W'):
            out.append((p['key'], 'oa', short(oa)))
        elif doi:
            out.append((p['key'], 'doi', doi))
    return out


def run_citing():
    c, cl = db(), Client()
    have = {k for k, in c.execute('select key from citing')}
    todo = [t for t in citing_targets() if t[0] not in have]
    log(stage='citing', todo=len(todo))
    wl = threading.Lock()

    def batch(chunk):
        kind = chunk[0][1]
        ids = [q for _, _, q in chunk]
        filt = ('openalex:' if kind == 'oa' else 'doi:') + '|'.join(ids)
        j = cl.get('/works', {'filter': filt, 'per-page': 50, 'select': CITING_SELECT})
        got = {}
        for w in j['results']:
            got[short(w['id']) if kind == 'oa' else (w.get('doi') or '').lower().replace('https://doi.org/', '')] = w
        rows = []
        for key, _, q in chunk:
            w = got.get(q)
            if w is None and kind == 'oa':  # merged or deleted: one free singleton follows a merge
                w = cl.get(f'/works/{q}', {'select': CITING_SELECT}, list_query=False)
            rows.append((key, f'{kind}:{q}', short(w['id']) if w else None, int(w is not None),
                         zlib.compress(json.dumps(w).encode()) if w else None, time.time()))
        with wl:
            c.executemany('insert or replace into citing values (?,?,?,?,?,?)', rows)
            c.execute('insert into requests values (?,?,?,?,?)', (time.time(), 'citing', len(chunk), 200, cl.remaining))
            c.commit()
        return sum(r[3] for r in rows)

    chunks = []
    for kind in ('oa', 'doi'):
        xs = [t for t in todo if t[1] == kind]
        chunks += [xs[i:i + 50] for i in range(0, len(xs), 50)]
    found = 0
    with ThreadPoolExecutor(4) as ex:
        for i, n in enumerate(ex.map(batch, chunks)):
            found += n
            if i % 100 == 0:
                log(stage='citing', done=i + 1, of=len(chunks), found=found, remaining=cl.remaining)
    log(stage='citing', done=len(chunks), found=found, remaining=cl.remaining)


def cited_ids(c):
    """{W id: number of citing papers} over every fetched citing paper."""
    from collections import Counter
    n = Counter()
    for (b,) in c.execute('select data from citing where status = 1'):
        w = json.loads(zlib.decompress(b))
        n.update({short(x) for x in w.get('referenced_works') or []})
    return n


def run_works():
    c, cl = db(), Client()
    n = cited_ids(c)
    have = {w for w, in c.execute('select wid from works')}
    todo = sorted((w for w in n if w not in have), key=lambda w: (-n[w], w))  # most-cited first, so a budget stop loses the tail
    log(stage='works', unique=len(n), have=len(have), todo=len(todo))
    wl = threading.Lock()
    chunks = [todo[i:i + 50] for i in range(0, len(todo), 50)]

    def batch(ids):
        j = cl.get('/works', {'filter': 'openalex:' + '|'.join(ids), 'per-page': 50, 'select': WORK_SELECT})
        got = {short(w['id']): w for w in j['results']}
        rows = [(q, int(q in got), zlib.compress(json.dumps(got[q]).encode()) if q in got else None, time.time()) for q in ids]
        with wl:
            c.executemany('insert or replace into works values (?,?,?,?)', rows)
            c.execute('insert into requests values (?,?,?,?,?)', (time.time(), 'works', len(ids), 200, cl.remaining))
            c.commit()
        return len(got)

    found = 0
    with ThreadPoolExecutor(6) as ex:
        for i, k in enumerate(ex.map(batch, chunks)):
            found += k
            if i % 200 == 0:
                log(stage='works', done=i + 1, of=len(chunks), found=found, remaining=cl.remaining)
    log(stage='works', done=len(chunks), found=found, remaining=cl.remaining)


def run_missing():
    """Singletons (free) for cited ids the list query did not return: a merged id resolves to its target."""
    c, cl = db(), Client()
    miss = [w for w, in c.execute('select wid from works where status = 0')]
    log(stage='missing', todo=len(miss))
    wl = threading.Lock()

    def one(q):
        w = cl.get(f'/works/{q}', {'select': WORK_SELECT}, list_query=False)
        with wl:
            if w:
                c.execute('update works set status = 2, data = ?, at = ? where wid = ?', (zlib.compress(json.dumps(w).encode()), time.time(), q))
            else:
                c.execute('update works set status = -1, at = ? where wid = ?', (time.time(), q))
        return int(w is not None)

    got = 0
    with ThreadPoolExecutor(4) as ex:
        for i, k in enumerate(ex.map(one, miss)):
            got += k
            if i % 500 == 0:
                with wl:
                    c.commit()
                log(stage='missing', done=i + 1, of=len(miss), resolved=got)
    c.commit()
    log(stage='missing', done=len(miss), resolved=got)


def status():
    c = db()
    log(citing=c.execute('select status, count(*) from citing group by status').fetchall(),
        works=c.execute('select status, count(*) from works group by status').fetchall(),
        last=c.execute('select * from requests order by t desc limit 1').fetchall())


if __name__ == '__main__':
    {'citing': run_citing, 'works': run_works, 'missing': run_missing, 'status': status}[sys.argv[1]]()
