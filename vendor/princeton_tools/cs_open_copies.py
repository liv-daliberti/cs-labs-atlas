# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/cs_open_copies.py (sha256 a0628efc07426dd1aee295892912227dbca994171bc4bdd81f26d92101580be5); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""More public copies of Princeton CS papers that have no local copy, staged for the full-text collector.

Targets: CS papers 2016–2026 without a local copy — catalog works linked to a CS unit (the 46 live units
and the staged provisional ones) and every work of the CS corpus (cs-complete/corpus_openalex.json),
including works that only exist in the pending catalog packages.

Sources (public metadata APIs, each at its documented rate; nothing behind a login or paywall):
  openalex  current OpenAlex locations (OPENALEX_API_KEY): open repository and preprint copies.
  s2        Semantic Scholar paper batch by DOI / arXiv ID: openAccessPdf, arXiv ID, ACL Anthology ID.
  dblp      CS faculty DBLP records via sparql.dblp.org (dblp.org serves a bot challenge; not bypassed) —
            PID from an official page, else an exact-name DBLP person accepted only as a bibliography anchor (>=5 of the faculty member's verified Princeton works, no rival
            exact-name profile reaching 20% of that). Electronic-edition links to arXiv (CoRR) and open
            proceedings (PMLR, NeurIPS, CVF, ACL Anthology, OpenReview, JMLR, IJCAI, IACR ePrint,
            USENIX, AAAI, LIPIcs), matched to targets by exact normalized title (+-3 years) and the
            faculty member on the target's byline.
  arxiv     arXiv API exact-title search (one request per 3 s, one connection) for targets with no arXiv
            candidate yet; accepted only for an identical normalized title, a shared author family
            name and a year within -3..+1.
package     discovery/claude-cs-open-copies-20261016/ (openalex, s2, dblp) and, with OPEN_COPIES_PACKAGE /
            OPEN_COPIES_SOURCES, discovery/claude-cs-open-copies-arxiv-20261016/ (arxiv): cs-open-copies-candidates.jsonl, evidence/,
            work-ids.txt (targets that gained a candidate, CS-unit works first), summary.json.
import      under .collector.lock, once the packages that add the pending works have been imported.

The collector re-checks robots.txt, downloads only these public URLs and verifies title/DOI in the file.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, hashlib, html, json, os, re, sqlite3, sys, time, unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import requests

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
FULLTEXT = P.STORES / 'princeton'
DISC = FULLTEXT / 'discovery'
PACKAGE = DISC / os.environ.get('OPEN_COPIES_PACKAGE', 'claude-cs-open-copies-20261016')  # the arXiv pass is its own package
SOURCES = os.environ.get('OPEN_COPIES_SOURCES', 'openalex,s2,dblp').split(',')
EVID = PACKAGE / 'evidence'
WORK = STAGE / 'cs-open-copies'
PENDING = ['claude-cs-complete-20261016', 'claude-cs-pi-works-20261015', 'claude-princeton-pi-works-20261016']
COPY = ('downloaded', 'fulltext_xml')
NOT_COPIES = {'doaj.org', 'pubmed.ncbi.nlm.nih.gov'}  # index / abstract pages, never the article file
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cs_complete import norm, toks


def nt(title):
    t = re.sub(r'<[^>]+>', ' ', html.unescape(title or ''))
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', t)


def family(name):
    t = toks(name or '')
    return t[-1] if t else ''


def arxiv_id(url):
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([^?#]+?)(?:v\d+)?(?:\.pdf)?/?$', url or '')
    return m.group(1) if m else None


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Client:
    def __init__(self):
        self.s = requests.Session(); self.s.headers['User-Agent'] = UA; self.last = {}

    def get(self, url, delay, method='GET', **kw):
        host = urlsplit(url).hostname
        for attempt in range(6):
            time.sleep(max(0, delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            try:
                r = self.s.request(method, url, timeout=(15, 90), **kw)
            except requests.RequestException:
                time.sleep(30 * (attempt + 1)); continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(int(r.headers.get('Retry-After') or 0) or 60 * (attempt + 1)); continue
            return r
        raise RuntimeError('giving up on ' + url.split('api_key')[0])


def cs_labs():
    labs = {u['lab_id'] for u in json.loads((STAGE / 'cs_units_live.json').read_text())}
    for name in ('claude-cs-complete-20261016', 'claude-cs-pi-works-20261015'):
        reg = json.loads((DISC / name / 'labs.json').read_text())
        labs |= set(reg) if isinstance(reg, dict) else {r.get('lab_id') or r.get('id') for r in reg}
    return labs


def graph_names(g):
    a = g.get('authors') or []
    if isinstance(a, str):
        a = re.split(r',| and ', a)
    if not isinstance(a, list):  # some graph nodes carry only an author count
        return []
    return [x if isinstance(x, str) else x.get('name') or x.get('display_name') or '' for x in a if isinstance(x, (str, dict))]


def targets():
    """Write cs-open-copies/targets.json."""
    WORK.mkdir(exist_ok=True)
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=300)
    labs = cs_labs()
    status = dict(db.execute('SELECT id,status FROM works'))
    by_doi = {d.lower(): i for i, d in db.execute('SELECT id,doi FROM works WHERE doi IS NOT NULL')}
    why = defaultdict(set)
    for w, l in db.execute('SELECT work_id,lab_id FROM work_lab_sources'):
        if l in labs:
            why[w].add('catalog_cs_unit_link')
    corpus = json.loads((STAGE / 'cs-complete/corpus_openalex.json').read_text())
    names = defaultdict(set)
    pending = {}
    for p in PENDING:
        for line in (DISC / p / 'new-works.jsonl').open():
            r = json.loads(line)
            pending.setdefault(r['id'], dict(r, package=p))
        for line in (DISC / p / 'associations.jsonl').open():
            a = json.loads(line)
            if a['lab_id'] in labs:
                why[a['work_id']].add('package_cs_unit_link')
    for w in corpus:
        wid = 'paper_oa_' + w['work'].rsplit('/', 1)[-1]
        doi = (w.get('doi') or '').lower().replace('https://doi.org/', '')
        if wid not in status and doi in by_doi:
            wid = by_doi[doi]
        why[wid].add('cs_corpus')
        names[wid] |= set(w['faculty']) | set(w['students'])
    audit = STAGE / 'cs-audit/units.json'
    for u in (json.loads(audit.read_text()) if audit.exists() else []):
        for p in u['papers'] + u['missing']:
            if p.get('catalog_id'):
                why[p['catalog_id']].add('live_cs_view')
    structure = STAGE / 'cs-structure/papers.json'  # every CS paper 2016–2026 with a CS person on it
    for p in (json.loads(structure.read_text()) if structure.exists() else []):
        wid = ('paper_oa_' + p['key'][2:]) if p['key'].startswith('W:') and 'paper_oa_' + p['key'][2:] in status else by_doi.get(p['doi']) if p['doi'] else None
        if wid:
            why[wid].add('cs_structure')
    out = []
    ids = [w for w in why if (w in status and status[w] not in COPY) or (w not in status and w in pending)]
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]; q = ','.join('?' * len(chunk))
        rows = {r[0]: r for r in db.execute(f'SELECT id,title,doi,year,graph_json,oa_json FROM works WHERE id IN ({q})', chunk)}
        cands = defaultdict(list)
        for w, u in db.execute(f'SELECT work_id,url FROM candidates WHERE work_id IN ({q})', chunk):
            cands[w].append(u)
        tried = defaultdict(dict)
        for w, u, s in db.execute(f'SELECT work_id,url,status FROM attempts WHERE work_id IN ({q})', chunk):
            tried[w][u] = s
        for wid in chunk:
            if wid in rows:
                _, title, doi, year, g, o = rows[wid]
                g = json.loads(g or '{}'); o = json.loads(o or 'null') or {}
                pkg = None
            else:
                r = pending[wid]; o = r.get('metadata') or {}; g = r['node']
                title, doi, year, pkg = g.get('name'), g.get('doi'), g.get('year'), r['package']
                cands[wid] = []
            people = set(names[wid]) | set(graph_names(g))
            people |= {a.get('author', {}).get('display_name') or '' for a in o.get('authorships') or []}
            W = (o.get('id') or g.get('openalex') or (wid if wid.startswith('paper_oa_') else '')).rsplit('/', 1)[-1].replace('paper_oa_', '') or None
            out.append(dict(id=wid, title=title or '', doi=(doi or '').lower().replace('https://doi.org/', '') or None,
                            year=int(year) if str(year or '').isdigit() else None, W=W, families=sorted({family(n) for n in people} - {''}),
                            why=sorted(why[wid]), package=pkg, candidates=cands[wid], attempts=tried[wid],
                            status=status.get(wid, 'pending_package')))
    (WORK / 'targets.json').write_text(json.dumps(out))
    c = Counter(t['status'] for t in out)
    print(json.dumps(dict(targets=len(out), by_status=c, with_doi=sum(1 for t in out if t['doi']), with_W=sum(1 for t in out if t['W']),
                          with_existing_candidate=sum(1 for t in out if t['candidates']),
                          with_unattempted_candidate=sum(1 for t in out if any(u not in t['attempts'] for u in t['candidates'])))))


def load_targets():
    return json.loads((WORK / 'targets.json').read_text())


def save_props(name, props):
    (WORK / f'{name}_proposals.json').write_text(json.dumps(props, indent=0))
    print(json.dumps({name: len(props), 'works': len({p['work_id'] for p in props})}))


def openalex():
    key = os.environ['OPENALEX_API_KEY']
    T = load_targets(); EVID.mkdir(parents=True, exist_ok=True)
    byW = defaultdict(list); byD = defaultdict(list)
    for t in T:
        if t['W']:
            byW[t['W']].append(t['id'])
        elif t['doi']:
            byD[t['doi']].append(t['id'])
    jobs = [('W', k) for k in byW] + [('doi', k) for k in byD]
    c = Client(); props = []
    sel = 'id,doi,title,ids,locations,best_oa_location'
    for n in range(0, len(jobs), 50):
        res = []
        for kind, v in jobs[n:n + 50]:  # single-work lookups are free; list queries spend the key's budget
            r = c.get('https://api.openalex.org/works/' + (v if kind == 'W' else 'doi:' + v), 0.12, params={'select': sel, 'api_key': key})
            if r.status_code == 200:
                res.append(dict(request=dict(work=v, select=sel), retrieved_at=now(), response=dict(results=[r.json()])))
        ev = EVID / f'openalex-{n // 50:03d}.json'
        ev.write_text(json.dumps(dict(source='OpenAlex works API (single-work records)', results=res)))
        for block in res:
            for w in block['response']['results']:
                wids = byW.get(w['id'].rsplit('/', 1)[-1], []) + byD.get((w.get('doi') or '').lower().replace('https://doi.org/', ''), [])
                for loc in w.get('locations') or []:
                    if not loc.get('is_oa'):
                        continue
                    src = loc.get('source') or {}
                    url = loc.get('pdf_url') or (loc.get('landing_page_url') if src.get('type') == 'repository' else None)
                    if not url or urlsplit(url).hostname in ('doi.org', 'dx.doi.org'):
                        continue
                    for wid in wids:
                        props.append(dict(work_id=wid, url=url, landing_url=loc.get('landing_page_url'), license=loc.get('license'),
                                          version=loc.get('version'), metadata_source=str(ev), source='openalex_location',
                                          detail=src.get('display_name')))
    save_props('openalex', props)


def s2():
    T = load_targets(); EVID.mkdir(parents=True, exist_ok=True)
    ids = defaultdict(list)
    for t in T:
        aid = t['doi'][len('10.48550/arxiv.'):] if t['doi'] and t['doi'].startswith('10.48550/arxiv.') else None
        if aid:
            ids['ARXIV:' + aid].append(t['id'])
        elif t['doi']:
            ids['DOI:' + t['doi']].append(t['id'])
    keys = list(ids); c = Client(); props = []
    for n in range(0, len(keys), 400):
        chunk = keys[n:n + 400]
        r = c.get('https://api.semanticscholar.org/graph/v1/paper/batch', 5, method='POST',
                  params={'fields': 'title,year,externalIds,openAccessPdf'}, json={'ids': chunk})
        r.raise_for_status()
        ev = EVID / f's2-batch-{n // 400:03d}.json'
        ev.write_text(json.dumps(dict(source='Semantic Scholar Graph API paper/batch', retrieved_at=now(), ids=chunk, response=r.json())))
        for k, p in zip(chunk, r.json()):
            if not p:
                continue
            ext = p.get('externalIds') or {}; oa = p.get('openAccessPdf') or {}
            found = []
            if oa.get('url') and 'semanticscholar.org' not in (urlsplit(oa['url']).hostname or ''):
                u = oa['url']
                found.append((u, None, oa.get('license'), 'submittedVersion' if arxiv_id(u) else ('publishedVersion' if oa.get('status') in ('GOLD', 'HYBRID', 'BRONZE') else None), 'openAccessPdf ' + str(oa.get('status'))))
            if ext.get('ArXiv'):
                a = ext['ArXiv']; found.append((f'https://arxiv.org/pdf/{a}', f'https://arxiv.org/abs/{a}', None, 'submittedVersion', 'externalIds.ArXiv'))
            if ext.get('ACL'):
                a = ext['ACL']; found.append((f'https://aclanthology.org/{a}.pdf', f'https://aclanthology.org/{a}/', None, 'publishedVersion', 'externalIds.ACL'))
            for wid in ids[k]:
                for u, land, lic, ver, d in found:
                    props.append(dict(work_id=wid, url=u, landing_url=land, license=lic, version=ver, metadata_source=str(ev), source='semantic_scholar', detail=d))
    save_props('s2', props)


def ee_links(ee, oa):
    """Electronic-edition link -> [(download url, landing url, version, license)] for open venues."""
    p = urlsplit(ee.strip()); h = (p.hostname or '').lower(); path = p.path; u = 'https://' + h + path + ('?' + p.query if p.query else '')
    if h in ('arxiv.org', 'www.arxiv.org') and arxiv_id(u):
        a = arxiv_id(u); return [(f'https://arxiv.org/pdf/{a}', f'https://arxiv.org/abs/{a}', 'submittedVersion', None)]
    if h == 'proceedings.mlr.press':
        m = re.match(r'/(v\d+)/([^/]+)\.html$', path)
        if m:
            v, k = m.groups(); return [(f'https://proceedings.mlr.press/{v}/{k}/{k}.pdf', u, 'publishedVersion', None)]
    if h in ('papers.nips.cc', 'proceedings.neurips.cc'):
        m = re.match(r'(/paper(?:_files/paper)?/\d{4})/hash/([0-9a-f]+)-Abstract(-[A-Za-z_]+)?\.html$', path)
        if m:
            b, k, suf = m.groups(); return [(f'https://{h}{b}/file/{k}-Paper{suf or ""}.pdf', u, 'publishedVersion', None)]
        return [(u, u, 'publishedVersion', None)]
    if h == 'openaccess.thecvf.com' and '/html/' in path and path.endswith('.html'):
        return [('https://openaccess.thecvf.com' + path.replace('/html/', '/papers/')[:-5] + '.pdf', u, 'publishedVersion', None)]
    if h in ('aclanthology.org', 'www.aclweb.org'):
        m = re.match(r'/(?:anthology/)?([A-Za-z0-9.\-]+?)(?:\.pdf)?/?$', path)
        if m:
            a = m.group(1); return [(f'https://aclanthology.org/{a}.pdf', f'https://aclanthology.org/{a}/', 'publishedVersion', None)]
    if h == 'openreview.net' and parse_qs(p.query).get('id'):
        i = parse_qs(p.query)['id'][0]; return [(f'https://openreview.net/pdf?id={i}', f'https://openreview.net/forum?id={i}', 'publishedVersion', None)]
    if h in ('jmlr.org', 'www.jmlr.org'):
        m = re.match(r'/papers/v(\d+)/([^/]+?)\.html$', path)
        if m:
            v, k = m.groups(); return [(f'https://jmlr.org/papers/volume{v}/{k}/{k}.pdf', u, 'publishedVersion', None)]
    if h in ('www.ijcai.org', 'ijcai.org'):
        m = re.match(r'/proceedings/(\d{4})/(\d+)/?$', path)
        if m:
            return [(f'https://www.ijcai.org/proceedings/{m[1]}/{m[2]}.pdf', u, 'publishedVersion', None)]
    if h == 'eprint.iacr.org':
        m = re.match(r'/(\d{4})/(\d+)/?$', path)
        if m:
            return [(f'https://eprint.iacr.org/{m[1]}/{m[2]}.pdf', u, 'submittedVersion', None)]
    if (h in ('www.usenix.org', 'usenix.org') and '/presentation/' in path) or h in ('ojs.aaai.org', 'drops.dagstuhl.de'):
        return [(u, u, 'publishedVersion', None)]
    if h in ('doi.org', 'dx.doi.org') and re.match(r'/10\.4230/lipics\.', path.lower()):
        return [('https://drops.dagstuhl.de/entities/document' + path, 'https://drops.dagstuhl.de/entities/document' + path, 'publishedVersion', 'cc-by')]
    if oa and path.lower().endswith('.pdf') and h not in ('doi.org', 'dx.doi.org'):
        return [(u, None, None, None)]
    return []


SPARQL = """PREFIX dblp: <https://dblp.org/rdf/schema#>
SELECT ?person ?name ?pub ?title ?year ?ee ?venue WHERE {
  VALUES %s { %s }
  ?person dblp:primaryCreatorName ?name .
  ?pub dblp:authoredBy ?person ; dblp:title ?title .
  OPTIONAL { ?pub dblp:yearOfPublication ?year }
  OPTIONAL { ?pub dblp:documentPage ?ee }
  OPTIONAL { ?pub dblp:publishedIn ?venue }
}"""


def dblp():
    """DBLP records (sparql.dblp.org; dblp.org itself serves a bot challenge) of verified CS faculty ->
    open-venue links for targets."""
    T = load_targets(); EVID.mkdir(parents=True, exist_ok=True); (WORK / 'raw' / 'dblp').mkdir(parents=True, exist_ok=True)
    corpus = json.loads((STAGE / 'cs-complete/corpus_openalex.json').read_text())
    faculty = json.loads((STAGE / 'cs-complete/faculty_verified.json').read_text())
    roster = {f['profile_id']: f for f in json.loads((STAGE / 'cs-roster/faculty_roster.json').read_text())}
    by_title = defaultdict(list)
    for t in T:
        if len(nt(t['title'])) >= 20:
            by_title[nt(t['title'])].append(t)
    c = Client(); props = []; people = []
    for f in faculty:
        mine = {nt(w['title']) for w in corpus if any(toks(n) == toks(f['name']) for n in w['faculty'])}
        official = []
        for l in roster.get(f['profile_id'], {}).get('identity_links') or []:
            m = re.search(r'dblp\.(?:org|uni-trier\.de)/pid/([A-Za-z0-9_/-]+?)(?:\.html|\.xml)?/?$', l.get('url', ''))
            if l.get('kind') == 'dblp' and m:
                official.append(('https://dblp.org/pid/' + m.group(1), l.get('source_url')))
        if official:
            q = SPARQL % ('?person', ' '.join('<%s>' % u for u, _ in official))
        else:
            q = SPARQL % ('?name', ' '.join(json.dumps(f['name'] + s) for s in [''] + [' %04d' % i for i in range(1, 10)]))
        cache = WORK / 'raw' / 'dblp' / (f['profile_id'] + '.json.gz')
        if cache.exists():
            got = json.loads(gzip.decompress(cache.read_bytes()))
        else:
            r = c.get('https://sparql.dblp.org/sparql', 10, params={'query': q, 'format': 'json'})
            got = dict(query=q, status=r.status_code, text=r.text, retrieved_at=now())
            cache.write_bytes(gzip.compress(json.dumps(got).encode()))
        rec = dict(name=f['name'], profile_id=f['profile_id'], verified_works=len(mine), http_status=got['status'])
        people.append(rec)
        if got['status'] != 200:
            continue
        pubs = defaultdict(lambda: defaultdict(lambda: dict(title='', year=None, ee=set(), venue='')))
        for b in json.loads(got['text'])['results']['bindings']:
            r = pubs[b['person']['value']][b['pub']['value']]
            r['title'] = b['title']['value']; r['venue'] = b.get('venue', {}).get('value', '')
            r['year'] = int(b['year']['value'][:4]) if b.get('year') else None
            if b.get('ee'):
                r['ee'].add(b['ee']['value'])
        scored = sorted(((sum(1 for r in recs.values() if nt(r['title'].rstrip('.')) in mine), pid) for pid, recs in pubs.items()), reverse=True)
        rec['persons'] = scored
        if official:
            accepted = [(pid, 'official_page_dblp_pid', next(s for u, s in official if u == pid)) for _, pid in scored]
        elif scored and scored[0][0] >= 5 and not any(n >= 0.2 * scored[0][0] for n, _ in scored[1:]):
            accepted = [(scored[0][1], 'dblp_bibliography_anchor', f'{scored[0][0]} of {len(mine)} verified Princeton works')]
        else:
            accepted = []
        rec['accepted'] = accepted
        fam = family(f['name'])
        for pid, method, basis in accepted:
            matched = []
            for key, r in pubs[pid].items():
                for t in by_title.get(nt(r['title'].rstrip('.')), []):
                    if t['year'] and r['year'] and abs(t['year'] - r['year']) > 3:
                        continue
                    if t['families'] and fam not in t['families']:
                        continue
                    links = [l for ee in sorted(r['ee']) for l in ee_links(ee, False)]
                    if links:
                        matched.append(dict(work_id=t['id'], record=dict(r, key=key, ee=sorted(r['ee'])), links=links))
            if not matched:
                continue
            ev = EVID / ('dblp-' + re.sub(r'[^A-Za-z0-9]+', '_', pid.rsplit('/pid/', 1)[-1]) + '.json')
            ev.write_text(json.dumps(dict(source='dblp SPARQL endpoint', endpoint='https://sparql.dblp.org/sparql', query=got['query'],
                                          response_sha256=sha(got['text'].encode()), retrieved_at=got['retrieved_at'], faculty=f['name'],
                                          dblp_person=pid, identity_method=method, identity_basis=basis, matched=matched)))
            for m in matched:
                for u, land, ver, lic in m['links']:
                    props.append(dict(work_id=m['work_id'], url=u, landing_url=land, license=lic, version=ver, metadata_source=str(ev),
                                      source='dblp_' + method, detail=m['record']['key']))
    (WORK / 'dblp_people.json').write_text(json.dumps(people, indent=1))
    print(json.dumps(dict(faculty=len(people), accepted=sum(1 for p in people if p.get('accepted')))))
    save_props('dblp', props)


def arxiv_have(T, sources):
    """work_id -> arXiv IDs it already has (catalog candidates, attempts, earlier passes' proposals)."""
    have = defaultdict(set)
    for t in T:
        for u in t['candidates'] + list(t['attempts']):
            if arxiv_id(u):
                have[t['id']].add(arxiv_id(u))
    for name in sources:
        p = WORK / f'{name}_proposals.json'
        for x in (json.loads(p.read_text()) if p.exists() else []):
            if arxiv_id(x['url']):
                have[x['work_id']].add(arxiv_id(x['url']))
    return have


def oa_arxiv():
    """arXiv versions through OpenAlex, whose arXiv preprint records are separate works (the arXiv search
    API was refusing requests: 503, then 429). title.search restricted to indexed_in:arxiv; the arXiv ID
    comes from the record's arXiv DOI or its arxiv.org location (records OpenAlex merged with the published
    version). Accepted only for an identical normalized title, a shared author family name and an arXiv
    year -1..+3 of the paper. Resumable; exits 75 when OpenAlex refuses (daily budget), to be rerun."""
    key = os.environ['OPENALEX_API_KEY']
    T = load_targets(); EVID.mkdir(parents=True, exist_ok=True)
    byid = {t['id']: t for t in T}
    have = arxiv_have(T, ('openalex', 's2', 'dblp'))
    done = {}
    for f in sorted(EVID.glob('openalex-arxiv-[0-9]*.json')):
        for q in json.loads(f.read_text())['queries']:
            done[q['work_id']] = q
    todo = [t for t in T if not have[t['id']] and t['id'] not in done and t['families'] and len(nt(t['title'])) >= 20]
    print(json.dumps(dict(todo=len(todo), done=len(done), at=now())), flush=True)
    c = Client(); buf = []
    def accept(t, w):
        doi = (w.get('doi') or '').lower().replace('https://doi.org/', '')
        aid = doi[len('10.48550/arxiv.'):] if doi.startswith('10.48550/arxiv.') else None
        for l in w.get('locations') or []:
            aid = aid or arxiv_id(l.get('landing_page_url') or '') or arxiv_id(l.get('pdf_url') or '')
        fams = {family((a.get('author') or {}).get('display_name')) for a in w.get('authorships') or []}
        y = w.get('publication_year')
        if aid and nt(w.get('title')) == nt(t['title']) and fams & set(t['families']) and (not t['year'] or not y or -1 <= t['year'] - y <= 3):
            return dict(arxiv_id=aid, openalex=w['id'], title=w.get('title'), year=y, shared_authors=sorted(fams & set(t['families'])))
    def flush(prefix):
        if buf:
            n = len(list(EVID.glob(prefix + '-[0-9]*.json')))
            (EVID / f'{prefix}-{n:03d}.json').write_text(json.dumps(dict(source='OpenAlex works API, arXiv-indexed records', rule=oa_arxiv.__doc__, queries=buf)))
            buf.clear()
    def get(params):
        r = c.s.get('https://api.openalex.org/works', params=dict(params, api_key=key), timeout=(15, 90))
        time.sleep(0.15)
        if r.status_code != 200:
            flush('openalex-arxiv' if 'title.search' in params['filter'] else 'openalex-arxiv-merged')
            print(json.dumps(dict(openalex_refused=r.status_code, detail=r.text[:200], at=now())), flush=True)
            sys.exit(75)
        return r.json().get('results', [])
    sel = 'id,doi,title,publication_year,authorships,locations'
    for t in todo:
        words = re.sub(r'[^A-Za-z0-9]+', ' ', unicodedata.normalize('NFKD', html.unescape(t['title'])).encode('ascii', 'ignore').decode()).split()
        params = {'filter': 'title.search:' + ' '.join(words) + ',indexed_in:arxiv', 'per_page': 10, 'select': sel}
        res = get(params)
        match = next((m for m in (accept(t, w) for w in res) if m), None)
        buf.append(dict(work_id=t['id'], request=params, http_status=200, retrieved_at=now(),
                        results=[dict(id=w['id'], doi=w.get('doi'), title=w.get('title'), year=w.get('publication_year')) for w in res], match=match))
        if len(buf) >= 100:
            flush('openalex-arxiv'); print(json.dumps(dict(queried=len(done) + len(buf))), flush=True)
    flush('openalex-arxiv')
    # queries from before locations were selected: same-title arXiv-indexed records without an arXiv DOI
    fixed = {q['work_id'] for f in EVID.glob('openalex-arxiv-merged-*.json') for q in json.loads(f.read_text())['queries']}
    redo = [(wid, r['id']) for wid, q in done.items() if not q['match'] and wid not in fixed
            for r in q['results'] if nt(r['title']) == nt(byid[wid]['title']) and 'arxiv' not in (r.get('doi') or '').lower()]
    for i in range(0, len(redo), 50):
        part = redo[i:i + 50]
        params = {'filter': 'openalex_id:' + '|'.join(sorted({w.rsplit('/', 1)[-1] for _, w in part})), 'per_page': 50, 'select': sel}
        res = {w['id']: w for w in get(params)}
        for wid in dict.fromkeys(w for w, _ in part):
            ws = [res[o] for x, o in part if x == wid and o in res]
            buf.append(dict(work_id=wid, request=params, http_status=200, retrieved_at=now(),
                            results=[dict(id=w['id'], doi=w.get('doi'), title=w.get('title'), year=w.get('publication_year')) for w in ws],
                            match=next((m for m in (accept(byid[wid], w) for w in ws) if m), None)))
        flush('openalex-arxiv-merged')
    props = []
    for f in sorted(EVID.glob('openalex-arxiv-*.json')):
        for q in json.loads(f.read_text())['queries']:
            if q['match']:
                a = q['match']['arxiv_id']
                props.append(dict(work_id=q['work_id'], url=f'https://arxiv.org/pdf/{a}', landing_url=f'https://arxiv.org/abs/{a}', license=None,
                                  version='submittedVersion', metadata_source=str(f), source='openalex_arxiv_exact_title', detail=a))
    save_props('oa_arxiv', props)


def arxiv():
    """Exact-title arXiv API search for targets that have no arXiv candidate yet (resumable)."""
    T = load_targets(); EVID.mkdir(parents=True, exist_ok=True); (WORK / 'raw').mkdir(exist_ok=True)
    have = arxiv_have(T, ('openalex', 's2', 'dblp', 'oa_arxiv'))
    state_p = WORK / 'arxiv_state.json'
    state = json.loads(state_p.read_text()) if state_p.exists() else dict(done={}, chunks=0)
    todo = [t for t in T if not have[t['id']] and t['id'] not in state['done'] and t['families'] and len(nt(t['title'])) >= 20]
    print(json.dumps(dict(todo=len(todo), done=len(state['done']))), flush=True)
    c = Client(); ns = {'a': 'http://www.w3.org/2005/Atom'}
    buf, raw = [], []
    def flush():
        if not buf:
            return
        n = state['chunks']; ev = EVID / f'arxiv-{n:03d}.json'
        ev.write_text(json.dumps(dict(source='arXiv API exact-title query', rule='identical normalized title, shared author family name, year -3..+1', queries=buf)))
        (WORK / 'raw' / f'arxiv-{n:03d}.jsonl.gz').write_bytes(gzip.compress('\n'.join(raw).encode()))
        for q in buf:
            state['done'][q['work_id']] = dict(match=q['match'], evidence=str(ev))
        state['chunks'] = n + 1
        state_p.write_text(json.dumps(state))
        buf.clear(); raw.clear()
    for t in todo:
        words = re.sub(r'[^A-Za-z0-9]+', ' ', unicodedata.normalize('NFKD', html.unescape(t['title'])).encode('ascii', 'ignore').decode()).split()
        q = 'ti:"' + ' '.join(words) + '"'
        time.sleep(max(0, 3.1 - (time.monotonic() - c.last.get('arxiv', 0))))
        c.last['arxiv'] = t0 = time.monotonic()
        try:  # no retries: when the API is unavailable, save progress and let arxiv_when_up.sh come back later
            r = c.s.get('https://export.arxiv.org/api/query', params={'search_query': q, 'max_results': 10}, timeout=(15, 90))
        except requests.RequestException as e:
            r = None; err = type(e).__name__
        if r is None or r.status_code != 200:
            flush()
            print(json.dumps(dict(api_unavailable=err if r is None else r.status_code, done=len(state['done']), at=now())), flush=True)
            sys.exit(75)
        if len(buf) % 25 == 0:
            print(json.dumps(dict(work_id=t['id'], seconds=round(time.monotonic() - t0, 1))), flush=True)
        match = None
        if r.status_code == 200:
            try:
                feed = ET.fromstring(r.content)
            except ET.ParseError:
                feed = None
            for e in (feed.findall('a:entry', ns) if feed is not None else []):
                title = e.findtext('a:title', '', ns); aid = arxiv_id(e.findtext('a:id', '', ns))
                fams = {family(a.findtext('a:name', '', ns)) for a in e.findall('a:author', ns)}
                year = int((e.findtext('a:published', '', ns) or '0')[:4] or 0)
                if aid and nt(title) == nt(t['title']) and fams & set(t['families']) and (not t['year'] or -1 <= t['year'] - year <= 3):
                    match = dict(arxiv_id=aid, title=' '.join(title.split()), authors=sorted(fams & set(t['families'])), published=e.findtext('a:published', '', ns))
                    break
        buf.append(dict(work_id=t['id'], query=q, http_status=r.status_code, response_sha256=sha(r.content), retrieved_at=now(), match=match))
        raw.append(json.dumps(dict(work_id=t['id'], status=r.status_code, body=r.text)))
        if len(buf) >= 25:
            flush(); print(json.dumps(dict(done=len(state['done']), matched=sum(1 for v in state['done'].values() if v['match']))), flush=True)
    flush()
    props = []
    for wid, v in state['done'].items():
        if v['match']:
            a = v['match']['arxiv_id']
            props.append(dict(work_id=wid, url=f'https://arxiv.org/pdf/{a}', landing_url=f'https://arxiv.org/abs/{a}', license=None,
                              version='submittedVersion', metadata_source=v['evidence'], source='arxiv_exact_title', detail=a))
    save_props('arxiv', props)


def package():
    T = {t['id']: t for t in load_targets()}
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=300)
    seen = defaultdict(set); seen_arx = defaultdict(set)
    for t in T.values():
        for u in t['candidates'] + list(t['attempts']):
            seen[t['id']].add(u.replace('http://', 'https://'))
            if arxiv_id(u):
                seen_arx[t['id']].add(arxiv_id(u))
    for w, u in db.execute('SELECT work_id,url FROM candidates'):
        if w in T:
            seen[w].add(u.replace('http://', 'https://'))
            if arxiv_id(u):
                seen_arx[w].add(arxiv_id(u))
    rows, counts, gained = [], Counter(), defaultdict(set)
    for other in DISC.glob('claude-cs-open-copies*/cs-open-copies-candidates.jsonl'):
        if other.parent != PACKAGE:
            for line in other.open():
                c = json.loads(line); seen[c['work_id']].add(c['url'])
                if arxiv_id(c['url']):
                    seen_arx[c['work_id']].add(arxiv_id(c['url']))
    for name in SOURCES:
        p = WORK / f'{name}_proposals.json'
        for x in (json.loads(p.read_text()) if p.exists() else []):
            u = x['url'].replace('http://', 'https://'); a = arxiv_id(u)
            if a:
                u = f'https://arxiv.org/pdf/{a}'
            if urlsplit(u).hostname in NOT_COPIES:
                counts['not_a_copy_host'] += 1; continue
            if u in seen[x['work_id']] or (a and a in seen_arx[x['work_id']]) or not Path(x['metadata_source']).is_file():
                counts['duplicate_' + name] += 1; continue
            seen[x['work_id']].add(u)
            if a:
                seen_arx[x['work_id']].add(a)
            rows.append(dict(x, url=u)); counts[x['source']] += 1; gained[x['work_id']].add(x['source'])
    PACKAGE.mkdir(parents=True, exist_ok=True)
    with open(PACKAGE / 'cs-open-copies-candidates.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    order = sorted(gained, key=lambda w: ('catalog_cs_unit_link' not in T[w]['why'], T[w]['status'] == 'pending_package', w))
    (PACKAGE / 'work-ids.txt').write_text('\n'.join(order) + '\n')
    hosts = Counter(urlsplit(r['url']).hostname for r in rows)
    summary = dict(created_at=now(), targets=len(T), candidates=len(rows), works_gaining_candidate=len(gained),
                   works_whose_first_candidate_this_is=sum(1 for w in gained if not T[w]['candidates']),
                   works_gaining_by_status=dict(Counter(T[w]['status'] for w in gained)), by_source=dict(counts),
                   top_hosts=hosts.most_common(25), requires_packages=sorted({T[w]['package'] for w in gained if T[w]['package']}),
                   rules=__doc__)
    (PACKAGE / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != 'rules'}, indent=1))


def import_catalog():
    """Insert the candidates under .collector.lock once the packages adding pending works are in."""
    import fcntl
    with (FULLTEXT / '.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(str(FULLTEXT / 'catalog.sqlite'), timeout=300)
        summary = json.loads((PACKAGE / 'summary.json').read_text())
        missing = [p for p in summary['requires_packages']
                   if not db.execute('SELECT 1 FROM receipts WHERE key=?', ('discovery:' + str(DISC / p),)).fetchone()]
        if missing:
            raise BlockingIOError('waiting for packages: ' + ', '.join(missing))
        n = Counter()
        for line in (PACKAGE / 'cs-open-copies-candidates.jsonl').open():
            c = json.loads(line)
            if not db.execute('SELECT 1 FROM works WHERE id=?', (c['work_id'],)).fetchone():
                n['work_missing'] += 1; continue
            n['candidates_added'] += db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',
                                                tuple(c[k] for k in ['work_id', 'url', 'landing_url', 'license', 'version', 'metadata_source'])).rowcount
        raw = (PACKAGE / 'summary.json').read_bytes()
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', ('discovery:' + str(PACKAGE), json.dumps(dict(
            path=str(PACKAGE), sha256=sha(raw), imported_at=now(), counts=dict(n)))))
        db.commit()
        print(json.dumps(dict(n)))


if __name__ == '__main__':
    {'targets': targets, 'openalex': openalex, 'oa_arxiv': oa_arxiv, 's2': s2, 'dblp': dblp, 'arxiv': arxiv, 'package': package,
     'import': import_catalog}[sys.argv[1]]()
