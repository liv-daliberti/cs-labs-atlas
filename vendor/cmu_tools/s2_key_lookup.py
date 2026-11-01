# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/s2_key_lookup.py (sha256 a7a41850d799325c2e7ebe5d1ed28368c4a6339713e6a1b667cbae9434170c03); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Semantic Scholar, with the user's API key, for papers without a local copy at Princeton CS, CMU SCS (in-scope
works) and EPFL IC (in-scope works, once its catalog exists).

The key is read from the environment (S2_API_KEY) only; it is never written to files, logs or packages. The key's
limit is one request per second across all endpoints: every request here waits 1.2 s after the previous one and
backs off on 429.

batch   POST /graph/v1/paper/batch, 500 ids per request (DOI, else arXiv id, else Princeton's stored CorpusId)
        -> title, year, externalIds, openAccessPdf, authors. A DOI or arXiv id names the paper exactly.
match   GET /graph/v1/paper/search/match for papers with none of those ids (normalized title of at least 20
        characters). A match counts only for an identical normalized title, a shared author family name with the
        paper's school people, and a year within 2.
use     ArXiv id      -> arXiv's bulk PDF copy (tools/arxiv_bulk.py listing, public GCS bucket) when no arXiv link
                         is known for the work yet
        PubMedCentral -> NLM's PMC open-data copy on S3 (pmc-oa-opendata; as tools/cmu_more_copies.py), PDF before XML
        ACL id        -> https://aclanthology.org/<id>.pdf
        openAccessPdf -> a candidate when it is a direct link on a host the collectors may use: not doi.org (the
                         publisher route already tries DOIs), arxiv.org (bulk copy instead), dl.acm.org and
                         openreview.net (403 to automated clients), aaai.org (12 h crawl delay), eprint.iacr.org
                         (robots), ssrn / osf / papers.ssrn (browser checks), core.ac.uk (403)
        The collectors check the paper's title in every downloaded file.
CMU / EPFL: candidates straight into data/fulltext/<school>/catalog.sqlite (evidence beside the catalog's other
discovery evidence). Princeton: package discovery/claude-s2key-<date><time>/ (cs_open_copies format; a new name each run), imported at a safe
phase by the Princeton import cycle.
cache raw/s2_key.jsonl (one record per lookup id; failures are retried on a later run)
usage: s2_key_lookup.py [princeton] [cmu] [epfl]     (default: all schools whose catalog exists)
       S2_BATCH_ONLY=1 skips the title matches (S2 answers about one per 19 s; leave them to a run that has the key
       to itself)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

STAGE = P.SWEEPS / 'claude-cmu-20261017'  # vendored: the data root (was Path(__file__).resolve().parents[1])
CACHE = STAGE / 'raw' / 's2_key.jsonl'
PRIN = P.SWEEPS / 'claude-princeton-20261015'
EPFL = P.SWEEPS / 'claude-epfl-20261019'
FT = P.STORES
API = 'https://api.semanticscholar.org/graph/v1'
FIELDS = 'title,year,externalIds,openAccessPdf,authors'
S3 = 'https://pmc-oa-opendata.s3.amazonaws.com'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
BAD_HOSTS = ('doi.org', 'arxiv.org', 'dl.acm.org', 'openreview.net', 'aaai.org', 'eprint.iacr.org', 'ssrn.com', 'osf.io', 'core.ac.uk')
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'princeton_tools'))
from cs_open_copies import nt, family, arxiv_id

# the pacing file sits on the shared project storage, so collectors on every node share the key's one request per 1.2 s
# (it was in one session's /tmp scratchpad, which compute nodes do not have: every s2 step there failed, 2026-10-28)
PACE = P.FT_LOGS / 's2-pace'  # data slot: the main checkout's logs/ whatever checkout or snapshot the code runs from


def wait_turn():
    """One S2 request per 1.2 s across every process using this module: the key's limit is cumulative."""
    import fcntl
    with open(PACE, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        try:
            last = float(f.read() or 0)
        except ValueError:
            last = 0.0
        time.sleep(max(0, last + 1.2 - time.time()))
        f.seek(0); f.truncate(); f.write(repr(time.time())); f.flush()


def s2(session, method, path, **kw):
    """One request to the S2 API at most every 1.2 s. 429 backs off (up to 2 min); a server error on one query is
    retried twice, then recorded (a later run asks again); None after repeated failures."""
    r = None
    for attempt in range(7):
        wait_turn()
        try:
            r = session.request(method, API + path, timeout=(15, 180), **kw)
        except Exception:
            time.sleep(20); continue
        if r.status_code in (200, 404, 400):
            return r
        if r.status_code == 429:
            time.sleep(min(120, 5 * 2 ** attempt)); continue
        if attempt >= 2:
            return r
        time.sleep(5)
    return r


# ---------------------------------------------------------------- targets

def princeton_targets():
    from catalog_snapshot import snapshot
    snap = snapshot(max_age_s=7200); st, dois = snap['status'], snap['doi']
    cid = {}
    for line in gzip.decompress((PRIN / 'cs-structure' / 'paper_meta.jsonl.gz').read_bytes()).decode().splitlines():
        r = json.loads(line)
        if (r.get('s2') or {}).get('corpus_id'):
            cid[r['key']] = r['s2']['corpus_id']
    papers = json.loads((PRIN / 'cs-structure' / 'papers.json').read_text())
    for f in ('oa_expand_papers.json', 'inst_sweep_papers.json'):
        if (PRIN / 'cs-structure' / f).exists():
            papers += json.loads((PRIN / 'cs-structure' / f).read_text())['papers']
    out, seen = [], set()
    for p in papers:
        w = ('paper_oa_' + p['key'][2:]) if p['key'].startswith('W:') and 'paper_oa_' + p['key'][2:] in st else dois.get(p.get('doi')) if p.get('doi') else None
        if not w or w in seen or st.get(w) in ('downloaded', 'fulltext_xml'):
            continue
        seen.add(w)
        people = (p.get('faculty') or []) + (p.get('students') or []) + [re.sub(r'^([^,]+),\s*(.+)$', r'\2 \1', x) for x in p.get('unrostered_unit_authors') or []]
        out.append(dict(school='princeton', work_id=w, doi=p.get('doi'), corpus=cid.get(p['key']), title=p.get('title'), year=p.get('year'), people=people))
    known = defaultdict(set)
    for src in (snap['candidates'], snap['attempts']):
        for w, us in src.items():
            known[w] |= set(us)
    for f in (FT / 'princeton' / 'discovery').glob('claude-*/*candidates.jsonl'):
        for line in f.open():
            c = json.loads(line); known[c['work_id']].add(c['url'])
    return out, known


def catalog_targets(school, scope_path):
    db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    scope = json.loads(scope_path.read_text())['scope']
    out = []
    for w, title, doi, year, g, status in db.execute('SELECT id, title, doi, year, graph_json, status FROM works'):
        if status in ('downloaded', 'fulltext_xml') or not scope.get(w, {}).get('in_scope'):
            continue
        g = json.loads(g)
        people = [n for k, v in g.items() if re.search(r'_(faculty|students|postdocs)$|^unit_authors_unrostered$', k) and isinstance(v, list) for n in v]
        out.append(dict(school=school, work_id=w, doi=doi, corpus=None, title=title, year=year, people=people))
    known = defaultdict(set)
    for t in ('candidates', 'attempts'):
        for w, u in db.execute(f'SELECT work_id, url FROM {t}'):
            known[w].add(u)
    lane = FT / school / 'staged' / 'arxiv-candidates.jsonl'
    if lane.exists():
        for line in lane.open():
            c = json.loads(line); known[c['work_id']].add(c['url'])
    return out, known


def lookup_id(t):
    d = (t['doi'] or '').lower()
    if d.startswith('10.48550/arxiv.'):
        return 'ARXIV:' + t['doi'][len('10.48550/arxiv.'):]
    if d:
        return 'DOI:' + t['doi']
    if t['corpus']:
        return f"CorpusId:{t['corpus']}"
    return None


# ---------------------------------------------------------------- lookups

def fetch(targets):
    import requests
    s = requests.Session(); s.headers['x-api-key'] = os.environ['S2_API_KEY']; s.headers['User-Agent'] = UA
    cache = {}
    if CACHE.exists():
        for line in CACHE.open():
            r = json.loads(line); cache[r['id']] = r
    ids = list(dict.fromkeys(i for t in targets if (i := lookup_id(t)) and (i not in cache or cache[i].get('error'))))
    titles = [] if os.environ.get('S2_BATCH_ONLY') else \
        list(dict.fromkeys(t['title'] for t in targets if not lookup_id(t) and len(nt(t['title'] or '')) >= 20
                           and ('match:' + nt(t['title']) not in cache or cache['match:' + nt(t['title'])].get('error'))))
    print(json.dumps(dict(targets=len(targets), batch_ids=len(ids), title_matches=len(titles), cached=len(cache))), flush=True)
    now = lambda: datetime.now(timezone.utc).isoformat()
    with CACHE.open('a') as f:
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            r = s2(s, 'POST', '/paper/batch', params={'fields': FIELDS}, json={'ids': chunk})
            res = r.json() if r is not None and r.status_code == 200 else None
            for k, lid in enumerate(chunk):
                rec = dict(id=lid, at=now(), data=res[k]) if res is not None else dict(id=lid, at=now(), error=r.status_code if r is not None else 'failed')
                cache[lid] = rec; f.write(json.dumps(rec) + '\n')
            f.flush()
            print(json.dumps(dict(batch_done=i + len(chunk), of=len(ids), ok=res is not None)), flush=True)
        for k, title in enumerate(titles):
            r = s2(s, 'GET', '/paper/search/match', params={'query': title, 'fields': FIELDS})
            lid = 'match:' + nt(title)
            if r is None or r.status_code not in (200, 404, 400):
                rec = dict(id=lid, at=now(), error=r.status_code if r is not None else 'failed')
            else:
                rec = dict(id=lid, at=now(), data=(r.json().get('data') or [None])[0] if r.status_code == 200 else None)
            cache[lid] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
            if k % 200 == 199:
                print(json.dumps(dict(matched=k + 1, of=len(titles))), flush=True)
    return cache


# ---------------------------------------------------------------- candidates

def ok_pdf(u):
    if not u or not u.startswith('http'):
        return False
    h = urlsplit(u).netloc.lower()
    return not any(h == b or h.endswith('.' + b) for b in BAD_HOSTS)


def pmc_files(session, pmcid, memo):
    if pmcid in memo:
        return memo[pmcid]
    time.sleep(1)
    try:
        r = session.get(f'{S3}/?list-type=2&prefix=PMC{pmcid}.', timeout=60)
        keys = re.findall(r'<Key>([^<]+)</Key>', r.text) if r.status_code == 200 else []
    except Exception:
        keys = []
    ver = max((int(x.group(1)) for k in keys if (x := re.search(r'\.(\d+)/', k))), default=None)
    memo[pmcid] = [f'{S3}/{k}' for ext in ('pdf', 'xml') if ver and (k := f'PMC{pmcid}.{ver}/PMC{pmcid}.{ver}.{ext}') in keys]
    return memo[pmcid]


def candidates(targets, known, cache):
    """[(target, url, landing, version, source, detail)] and counts."""
    import requests
    from arxiv_bulk import listing
    s3 = requests.Session(); s3.headers['User-Agent'] = UA
    rows, n, memo, want_arxiv = [], Counter(), {}, {}
    for t in targets:
        lid = lookup_id(t)
        rec = cache.get(lid) if lid else cache.get('match:' + nt(t['title'] or ''))
        d = (rec or {}).get('data')
        if not d:
            n['no_record'] += 1; continue
        if not lid:  # a title match must be the same paper
            fams = {family(a.get('name') or '') for a in d.get('authors') or []}
            if nt(d.get('title') or '') != nt(t['title']) or not fams & {family(x) for x in t['people']} or \
                    (t['year'] and d.get('year') and abs(t['year'] - d['year']) > 2):
                n['match_rejected'] += 1; continue
            n['match_accepted'] += 1
        n['found'] += 1
        ext = d.get('externalIds') or {}
        w, k = t['work_id'], known[t['work_id']]
        a = ext.get('ArXiv') or arxiv_id((d.get('openAccessPdf') or {}).get('url') or '')
        if a and not any(arxiv_id(u) for u in k):
            want_arxiv[(t['school'], w)] = (t, a)
        if ext.get('PubMedCentral') and not any('pmc-oa-opendata' in u for u in k):
            pmcid = re.sub(r'\D', '', str(ext['PubMedCentral']))
            for u in pmc_files(s3, pmcid, memo):
                rows.append((t, u, f'https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/', None, 's2_pmc_open_data', pmcid)); n['pmc'] += 1
        if ext.get('ACL'):
            u = f"https://aclanthology.org/{ext['ACL']}.pdf"
            if u not in k:
                rows.append((t, u, f"https://aclanthology.org/{ext['ACL']}/", 'publishedVersion', 's2_acl_anthology', ext['ACL'])); n['acl'] += 1
        oa = d.get('openAccessPdf') or {}
        u = oa.get('url') or ''
        if ok_pdf(u) and u not in k:
            rows.append((t, u, None, None, 's2_open_access_pdf', oa.get('status'))); n['open_access_pdf'] += 1
        elif u:
            n['open_access_pdf_skipped_host'] += 1
    urls = listing([a for _, a in want_arxiv.values()])
    for (school, w), (t, a) in want_arxiv.items():
        if urls.get(a):
            rows.append((t, urls[a], f'https://arxiv.org/abs/{a}', 'submittedVersion', 's2_arxiv_bulk_gcs', a)); n['arxiv_bulk'] += 1
        else:
            n['arxiv_not_in_bulk'] += 1
    for t, u, *_ in rows:
        known[t['work_id']].add(u)
    return rows, n


def write(school, rows, cache_ids):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    lookups = {i: cache_ids[i] for i in cache_ids}
    if school == 'princeton':
        pkg = FT / 'princeton' / 'discovery' / f"claude-s2key-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
        (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
        ev = pkg / 'evidence' / 's2-key.json'
        ev.write_text(json.dumps(dict(rule=__doc__, lookups=lookups)))
        out = [dict(work_id=t['work_id'], url=u, landing_url=land, license=None, version=ver, metadata_source=str(ev), source=src, detail=det)
               for t, u, land, ver, src, det in rows]
        with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
            for r in out:
                f.write(json.dumps(r) + '\n')
        (pkg / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in out)) + '\n')
        (pkg / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(Counter(r['source'] for r in out)),
                                                          works_gaining_candidate=len({r['work_id'] for r in out}), requires_packages=[], rules=__doc__), indent=1))
        return dict(package=str(pkg), rows=len(out), works=len({r['work_id'] for r in out}))
    evdir = FT / school / 'discovery' / f'claude-{school}-catalog' / 'evidence'
    evdir.mkdir(parents=True, exist_ok=True)
    ev = evdir / f's2-key-{stamp}.json'
    ev.write_text(json.dumps(dict(rule=__doc__, lookups=lookups)))
    db = sqlite3.connect(str(FT / school / 'catalog.sqlite'), timeout=300)
    for attempt in range(20):  # the collector writes to the same catalog: wait out its locks
        try:
            added = 0
            for t, u, land, ver, src, det in rows:
                added += db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (t['work_id'], u, land, None, ver, str(ev))).rowcount
            db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(30)
    return dict(candidates_added=added, works=len({t['work_id'] for t, *_ in rows}))


def main():
    schools = sys.argv[1:] or [s for s in ('princeton', 'cmu', 'epfl') if (FT / s / 'catalog.sqlite').exists()]
    plan = {}
    for school in schools:
        if school == 'princeton':
            plan[school] = princeton_targets()
        elif school == 'cmu':
            plan[school] = catalog_targets('cmu', STAGE / 'people' / 'scope.json')
        elif school == 'epfl' and (EPFL / 'people' / 'scope.json').exists():
            plan[school] = catalog_targets('epfl', EPFL / 'people' / 'scope.json')
    cache = fetch([t for ts, _ in plan.values() for t in ts])
    for school, (ts, known) in plan.items():
        rows, n = candidates(ts, known, cache)
        used = {i: cache[i] for t in ts if (i := lookup_id(t) or 'match:' + nt(t['title'] or '')) in cache}
        print(json.dumps(dict(school=school, missing=len(ts), **n, **write(school, rows, used))), flush=True)


if __name__ == '__main__':
    main()
