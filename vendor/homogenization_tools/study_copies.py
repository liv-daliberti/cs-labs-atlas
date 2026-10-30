# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-homogenization-20261019/tools/study_copies.py (sha256 0a59c2a219a0c3fe49dce06dd2bc02ef7031a15092077986ab10e9ea17d4d77c); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Open copies for the study-set papers (corpus/papers.jsonl.gz) that have no local full text, at all four schools.

The schools' own discovery passes worked from their catalogs' in-scope works; the study set also holds lab-record
additions and OpenAlex-affiliation papers they never asked about, and MIT never had the arXiv title match or the
Semantic Scholar lookup. This pass asks both for exactly the study set's missing papers:

  missing  a study-set paper is matched to its catalog work by work key, else DOI, else normalized title (read-only,
           rowid-chunked catalog reads); papers with a copy under any catalog work sharing their key, DOI or normalized title
           are skipped (the coverage count's rule; duplicates across a school's sources are common).
  arxiv    papers with no arXiv link yet: the arXiv id the corpus already records, else a match in the local arXiv OAI
           index (../claude-cmu-20261017/tools/arxiv_oai.py match_one: exact normalized title, the same significant
           title words, or title with/without subtitle; every tier needs a family name shared with the paper's school
           faculty or students and a first version from 1 year after to 3 years before the paper). A leading session
           number ('14.5 Eyeriss: ...') is dropped for a second try. The PDF comes from arXiv's bulk copy on GCS
           (arxiv_bulk.listing), never arxiv.org.
  s2       papers with a DOI: Semantic Scholar /paper/batch with the user's key (../claude-cmu-20261017/tools/
           s2_key_lookup.py fetch + candidates: ArXiv id -> bulk copy, PMCID -> PMC open-data S3, ACL id ->
           aclanthology.org, openAccessPdf on a host the collectors may use). The key is read from S2_API_KEY only.
  core     papers with a DOI: CORE's search API, 25 DOIs per request (../claude-cmu-20261017/tools/core_search.py: its
           cache, pacing and link filter - repository links CORE records, without core.ac.uk, publishers, doi.org and
           the hosts the collectors cannot use). The key is read from CORE_API_KEY only.
  figshare papers whose links or DOI name a Figshare article (KiltHub, CMU's repository, is Figshare: DOI 10.1184/R1/<id>,
           kilthub.cmu.edu / figshare.com /articles/.../<id>; also 10.6084/m9.figshare.<id>): the article page is a script
           app the collector cannot read ('neither a PDF nor an HTML landing page'), so Figshare's public API
           (api.figshare.com/v2/articles/<id>; no robots.txt, one request per second) lists the files; each PDF that is
           not link-only and <= 500 MiB becomes https://ndownloader.figshare.com/files/<file id> (redirects to the signed
           store approved in ../claude-cmu-20261017/tools/collector_wrapper.py). Cached in raw/figshare_articles.jsonl.
Candidates for CMU / EPFL / MIT go straight into data/fulltext/<school>/catalog.sqlite (INSERT OR IGNORE; evidence
discovery/claude-<school>-catalog/evidence/study-copies-<stamp>.json); Princeton's become the package
discovery/claude-study-copies-<stamp>/ (cs_open_copies format) for the import cycle. The collectors' identity check
(the catalog title in the file) applies to every candidate.
  pmc      papers with a PubMed Central article link (robots.txt disallows www.ncbi.nlm.nih.gov/pmc/articles/*) and no
           PMC open-data copy yet: the article's files in NLM's PMC Open Access dataset on AWS (pmc-oa-opendata, public S3
           listing, one per second), PDF before JATS XML (as ../claude-mit-20261020/tools/mit_more_copies.py).
  openalex papers with a DOI that have no candidate at all, and every missing Princeton paper (its lab-record and
           affiliation additions never went through Princeton's discovery): OpenAlex single-work records by DOI (free with
           the key, OPENALEX_API_KEY from the environment only; 8 per second), every open location's pdf_url on a host the
           collectors may use (s2_key_lookup.ok_pdf), a repository's landing page (core_search.usable), arXiv locations
           through the bulk copy, PMC locations through the PMC step. Cached in raw/openalex_by_doi.jsonl.
  lane     papers whose only arXiv link is an arxiv.org candidate staged for the arXiv windows
           (data/fulltext/<school>/staged/arxiv-candidates.jsonl): the same arXiv id through the bulk copy on GCS.
usage: study_copies.py [arxiv] [s2] [core] [figshare] [pmc] [openalex] [lane] [--schools princeton,cmu,epfl,mit] [--dry]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sqlite3, sys, time, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.HOMOGENIZATION_STUDY  # vendored: the data root (was Path(__file__).resolve().parents[1])
CMU_TOOLS = Path(__file__).resolve().parents[1] / 'cmu_tools'
PRIN_TOOLS = Path(__file__).resolve().parents[1] / 'princeton_tools'
FT = P.STORES
sys.path.insert(0, str(CMU_TOOLS)); sys.path.insert(0, str(PRIN_TOOLS))
from cs_open_copies import arxiv_id

SESSION = re.compile(r'^\s*\d+(?:\.\d+)+\s+(?=\S)')


def nt(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', t)


def chunks(db, table, cols, n=20000):
    hi = db.execute(f'SELECT MAX(rowid) FROM {table}').fetchone()[0] or 0
    for lo in range(0, hi + 1, n):
        yield from db.execute(f'SELECT {cols} FROM {table} WHERE rowid >= ? AND rowid < ?', (lo, lo + n)).fetchall()
        time.sleep(0.05)


def missing(school, rows):
    """[(study row, catalog work id)] without a local copy, and {work id: URLs already known} for those works."""
    db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    status, key, have = {}, {}, set()
    for i, title, doi, st in chunks(db, 'works', 'id, title, doi, status'):
        status[i] = st
        if doi:
            key.setdefault('doi:' + doi.lower(), i)
        if title:
            key.setdefault('t:' + nt(title), i)
        if st in ('downloaded', 'fulltext_xml'):  # a copy under any catalog work with the same DOI or title covers the paper (as the coverage count does)
            have.update(x for x in (i, doi and 'doi:' + doi.lower(), title and 't:' + nt(title)) if x)
    out = []
    for r in rows:
        if r.get('work_key') in have or (r.get('doi') and 'doi:' + r['doi'].lower() in have) or 't:' + nt(r['title']) in have:
            continue
        w = r.get('work_key') if r.get('work_key') in status else (key.get('doi:' + r['doi'].lower()) if r.get('doi') else None) or key.get('t:' + nt(r['title']))
        if w and status[w] not in ('downloaded', 'fulltext_xml'):
            out.append((r, w))
    want = {w for _, w in out}
    known = defaultdict(set)
    for t in ('candidates', 'attempts'):
        for w, u in chunks(db, t, 'work_id, url'):
            if w in want:
                known[w].add(u)
    lane = FT / school / 'staged' / 'arxiv-candidates.jsonl'
    if lane.exists():
        for line in lane.open():
            c = json.loads(line)
            if c['work_id'] in want:
                known[c['work_id']].add(c['url'])
    if school == 'princeton':
        for f in (FT / 'princeton' / 'discovery').glob('claude-*/*candidates.jsonl'):
            for line in f.open():
                c = json.loads(line)
                if c['work_id'] in want:
                    known[c['work_id']].add(c['url'])
    db.close()
    return out, known


def has_arxiv(urls):
    return any(arxiv_id(u) or 'arxiv-dataset/arxiv/arxiv/pdf/' in u for u in urls)


def arxiv_rows(plan, n):
    import arxiv_oai
    from arxiv_bulk import listing
    idx = arxiv_oai.index()
    print(json.dumps(dict(arxiv_titles=len(idx[0]))), flush=True)
    want = {}
    for school, (miss, known) in plan.items():
        for r, w in miss:
            if has_arxiv(known[w]):
                continue
            if r.get('arxiv'):
                want[(school, w)] = (r['arxiv'], 'corpus_arxiv_id'); n[f'{school}:corpus_arxiv_id'] += 1; continue
            people = (r.get('faculty') or []) + (r.get('students') or [])
            aid, tier = arxiv_oai.match_one(idx, r['title'], r['year'], people)
            if not aid and SESSION.match(r['title'] or ''):
                aid, tier = arxiv_oai.match_one(idx, SESSION.sub('', r['title']), r['year'], people)
                tier = tier and tier + '_without_session_number'
            if aid:
                want[(school, w)] = (aid, tier); n[f'{school}:{tier}'] += 1
    urls = listing([a for a, _ in want.values()])
    rows = defaultdict(list)
    for (school, w), (a, tier) in want.items():
        if urls.get(a):
            rows[school].append(dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', version='submittedVersion',
                                     source='study_arxiv_' + tier, detail=a))
        else:
            n[f'{school}:arxiv_not_in_bulk'] += 1
    return rows


def s2_rows(plan, n):
    import s2_key_lookup as s2k
    import os
    os.environ.setdefault('S2_BATCH_ONLY', '1')
    targets = {school: [dict(school=school, work_id=w, doi=r.get('doi'), corpus=None, title=r['title'], year=r['year'],
                             people=(r.get('faculty') or []) + (r.get('students') or [])) for r, w in miss if r.get('doi')]
               for school, (miss, _) in plan.items()}
    cache = s2k.fetch([t for ts in targets.values() for t in ts])
    rows = defaultdict(list)
    for school, ts in targets.items():
        known = plan[school][1]
        found, cn = s2k.candidates(ts, known, cache)
        for k, v in cn.items():
            n[f'{school}:s2_{k}'] += v
        for t, u, land, ver, src, det in found:
            rows[school].append(dict(work_id=t['work_id'], url=u, landing_url=land, version=ver, source='study_' + src, detail=det))
    return rows


def core_rows(plan, n):
    import os, requests
    import core_search as cs
    s = requests.Session(); s.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']
    done = {}
    if cs.CACHE.exists():
        for line in cs.CACHE.open():
            r = json.loads(line); done[r['doi']] = r
    dois = [r['doi'].lower() for miss, _ in plan.values() for r, _ in miss if r.get('doi') and not r['doi'].lower().startswith('10.48550/')]
    todo = list(dict.fromkeys(d for d in dois if '"' not in d and '\\' not in d and (d not in done or done[d].get('error'))))
    print(json.dumps(dict(core_dois=len(set(dois)), todo=len(todo), cached=len(done))), flush=True)
    with cs.CACHE.open('a') as f:
        for i in range(0, len(todo), 25):
            chunk = todo[i:i + 25]
            q = ' OR '.join(f'doi:"{d}"' for d in chunk)
            res = None
            for attempt in range(4):
                time.sleep(2)
                try:
                    r = s.get('https://api.core.ac.uk/v3/search/outputs/', params={'q': q, 'limit': 100}, timeout=(15, 200))
                except Exception:
                    time.sleep(30); continue
                left = r.headers.get('x-ratelimit-remaining')
                if r.status_code == 200:
                    res = r.json().get('results') or []
                    if left is not None and int(left) < 5:
                        time.sleep(60)
                    break
                time.sleep(120 if r.status_code == 429 else 20)
            got = defaultdict(list)
            for o in res or []:
                d = (o.get('doi') or '').lower()
                if d in chunk:
                    got[d] += [u for u in (o.get('sourceFulltextUrls') or []) + [o.get('downloadUrl') or ''] if u]
            at = datetime.now(timezone.utc).isoformat()
            for d in chunk:
                rec = dict(doi=d, at=at, links=list(dict.fromkeys(got.get(d, [])))) if res is not None else dict(doi=d, at=at, error=True)
                done[d] = rec; f.write(json.dumps(rec) + '\n')
            f.flush()
            if (i // 25) % 40 == 39:
                print(json.dumps(dict(core_asked=i + len(chunk), of=len(todo))), flush=True)
    rows = defaultdict(list)
    for school, (miss, known) in plan.items():
        for r, w in miss:
            if not r.get('doi'):
                continue
            for u in (done.get(r['doi'].lower()) or {}).get('links') or []:
                if cs.usable(u) and u not in known[w]:
                    rows[school].append(dict(work_id=w, url=u, landing_url=u, version=None, source='study_core_search', detail=r['doi']))
                    known[w].add(u); n[f'{school}:core_links'] += 1
    return rows


FIG_URL = re.compile(r'(?:figshare\.com|kilthub\.cmu\.edu)/articles/(?:[^/?#]+/)*?(\d{6,9})(?:/\d{1,3})?/?(?:[?#].*)?$')
FIG_DOI = re.compile(r'10\.1184/r1/(\d{6,9})|10\.6084/m9\.figshare\.(\d{6,9})', re.I)


def figshare_rows(plan, n):
    import requests
    cache_f = STAGE / 'raw' / 'figshare_articles.jsonl'
    cache = {}
    if cache_f.exists():
        for line in cache_f.open():
            r = json.loads(line); cache[r['id']] = r
    want = defaultdict(set)
    for school, (miss, known) in plan.items():
        for r, w in miss:
            ids = set()
            for u in list(known[w]) + ['doi:' + (r.get('doi') or '')]:
                m = FIG_URL.search(u) or FIG_DOI.search(u)
                if m:
                    ids.add(next(g for g in m.groups() if g))
            for i in ids:
                want[i].add((school, w))
    todo = [i for i in want if i not in cache or cache[i].get('error')]
    print(json.dumps(dict(figshare_articles=len(want), todo=len(todo))), flush=True)
    s = requests.Session(); s.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
    cache_f.parent.mkdir(parents=True, exist_ok=True)
    with cache_f.open('a') as f:
        for k, i in enumerate(todo):
            rec = None
            for attempt in range(4):
                time.sleep(1)
                try:
                    r = s.get(f'https://api.figshare.com/v2/articles/{i}', timeout=(15, 60))
                except Exception as e:
                    rec = dict(error=str(e)[:100]); time.sleep(20); continue
                if r.status_code == 429:
                    rec = dict(error=429); time.sleep(int(r.headers.get('Retry-After') or 60)); continue
                if r.status_code != 200:
                    rec = dict(error=r.status_code) if r.status_code >= 500 else dict(files=[], status=r.status_code); break
                d = r.json()
                rec = dict(title=d.get('title'), doi=d.get('doi'), type=d.get('defined_type_name'), url=d.get('url_public_html'),
                           files=[dict(id=x['id'], name=x.get('name'), size=x.get('size'), mimetype=x.get('mimetype'), link_only=x.get('is_link_only'))
                                  for x in d.get('files') or []])
                break
            rec = dict(id=i, at=datetime.now(timezone.utc).isoformat(), **rec)
            cache[i] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
            if k % 200 == 199:
                print(json.dumps(dict(figshare_asked=k + 1, of=len(todo))), flush=True)
    rows = defaultdict(list)
    for i, works in want.items():
        rec = cache.get(i) or {}
        pdfs = [x for x in rec.get('files') or [] if not x.get('link_only') and (x.get('size') or 0) <= 500 * 1024 * 1024
                and ((x.get('mimetype') or '') == 'application/pdf' or (x.get('name') or '').lower().endswith('.pdf'))]
        n['figshare_articles_with_pdf' if pdfs else 'figshare_articles_without_pdf'] += 1
        for school, w in works:
            for x in pdfs:
                u = f"https://ndownloader.figshare.com/files/{x['id']}"
                if u not in plan[school][1][w]:
                    rows[school].append(dict(work_id=w, url=u, landing_url=rec.get('url') or f'https://figshare.com/articles/{i}', version=None,
                                             source='study_figshare_api', detail=i))
                    plan[school][1][w].add(u); n[f'{school}:figshare_files'] += 1
    return rows


PMC_LINK = re.compile(r'(?:ncbi\.nlm\.nih\.gov/pmc/articles|pmc\.ncbi\.nlm\.nih\.gov/articles|europepmc\.org/articles)/(?:PMC)?(\d+)', re.I)


def pmc_rows(plan, n):
    import requests
    import s2_key_lookup as s2k
    s = requests.Session(); s.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
    memo, rows = {}, defaultdict(list)
    for school, (miss, known) in plan.items():
        for r, w in miss:
            ids = {m.group(1) for u in known[w] if (m := PMC_LINK.search(u))}
            if not ids or any('pmc-oa-opendata' in u for u in known[w]):
                continue
            for pmcid in sorted(ids):
                files = s2k.pmc_files(s, pmcid, memo)
                n[f'{school}:pmc_with_open_data' if files else f'{school}:pmc_not_in_open_data'] += 1
                for u in files:
                    if u not in known[w]:
                        rows[school].append(dict(work_id=w, url=u, landing_url=f'https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/', version=None,
                                                 source='study_pmc_open_data', detail=pmcid))
                        known[w].add(u)
    return rows


def openalex_rows(plan, n):
    import os, requests
    import s2_key_lookup as s2k, core_search as cs
    from arxiv_bulk import listing
    key = os.environ['OPENALEX_API_KEY']
    cache_f = STAGE / 'raw' / 'openalex_by_doi.jsonl'
    cache = {}
    if cache_f.exists():
        for line in cache_f.open():
            r = json.loads(line); cache[r['doi']] = r
    want = defaultdict(set)
    for school, (miss, known) in plan.items():
        for r, w in miss:
            d = (r.get('doi') or '').lower()
            if d and not d.startswith('10.48550/') and (school == 'princeton' or not known[w]):
                want[d].add((school, w))
    todo = [d for d in want if d not in cache or cache[d].get('error')]
    print(json.dumps(dict(openalex_dois=len(want), todo=len(todo))), flush=True)
    s = requests.Session(); s.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
    sel = 'id,doi,title,locations,best_oa_location'
    cache_f.parent.mkdir(parents=True, exist_ok=True)
    last = 0.0
    with cache_f.open('a') as f:
        for k, d in enumerate(todo):
            rec = None
            for attempt in range(4):
                time.sleep(max(0, 0.12 - (time.monotonic() - last))); last = time.monotonic()
                try:
                    r = s.get('https://api.openalex.org/works/doi:' + d, params={'select': sel, 'api_key': key}, timeout=(15, 60))
                except Exception as e:
                    rec = dict(error=str(e)[:80]); time.sleep(10); continue
                if r.status_code == 429:
                    rec = dict(error=429); time.sleep(30); continue
                if r.status_code == 404:
                    rec = dict(locations=[]); break
                if r.status_code != 200:
                    rec = dict(error=r.status_code); time.sleep(5); continue
                j = r.json()
                rec = dict(id=j.get('id'), locations=[dict(pdf_url=l.get('pdf_url'), landing=l.get('landing_page_url'), is_oa=l.get('is_oa'), version=l.get('version'),
                                                           license=l.get('license'), source=(l.get('source') or {}).get('display_name'), source_type=(l.get('source') or {}).get('type'))
                                                      for l in j.get('locations') or []])
                break
            rec = dict(doi=d, at=datetime.now(timezone.utc).isoformat(), **rec)
            cache[d] = rec; f.write(json.dumps(rec) + '\n')
            if k % 500 == 499:
                f.flush(); print(json.dumps(dict(openalex_asked=k + 1, of=len(todo))), flush=True)
    rows, arx = defaultdict(list), {}
    for d, works in want.items():
        for loc in (cache.get(d) or {}).get('locations') or []:
            if not loc.get('is_oa'):
                continue
            pdf, land = loc.get('pdf_url') or '', loc.get('landing') or ''
            a = arxiv_id(pdf) or arxiv_id(land)
            if a:
                for school, w in works:
                    arx[(school, w)] = a
                continue
            if 'ncbi.nlm.nih.gov' in pdf + land or 'europepmc.org' in pdf + land:
                for school, w in works:
                    plan[school][1][w].add(pdf or land)  # the PMC step takes it from here
                n['openalex_pmc_links'] += 1
                continue
            if s2k.ok_pdf(pdf) and cs.usable(pdf):
                url = pdf
            elif loc.get('source_type') == 'repository' and cs.usable(land) and s2k.ok_pdf(land):
                url = land
            else:
                continue
            for school, w in works:
                if url not in plan[school][1][w]:
                    rows[school].append(dict(work_id=w, url=url, landing_url=land or None, version=loc.get('version'), source='study_openalex_location', detail=loc.get('source')))
                    plan[school][1][w].add(url); n[f'{school}:openalex_links'] += 1
    arx = {k: a for k, a in arx.items() if not has_arxiv(plan[k[0]][1][k[1]])}
    urls = listing(list(arx.values()))
    for (school, w), a in arx.items():
        if urls.get(a):
            rows[school].append(dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', version='submittedVersion', source='study_openalex_arxiv_bulk', detail=a))
            plan[school][1][w].add(urls[a]); n[f'{school}:openalex_arxiv'] += 1
    return rows


def lane_rows(plan, n):
    from arxiv_bulk import listing
    want = {}
    for school, (miss, known) in plan.items():
        ids = {w for _, w in miss}
        f = FT / school / 'staged' / 'arxiv-candidates.jsonl'
        if not f.exists():
            continue
        for line in f.open():
            c = json.loads(line)
            if c['work_id'] in ids and not any('arxiv-dataset/arxiv/arxiv/pdf/' in u for u in known[c['work_id']]):
                a = arxiv_id(c['url'])
                if a:
                    want[(school, c['work_id'])] = re.sub(r'v\d+$', '', a)
    urls = listing(list(want.values()))
    rows = defaultdict(list)
    for (school, w), a in want.items():
        if urls.get(a):
            rows[school].append(dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', version='submittedVersion', source='study_lane_arxiv_bulk', detail=a))
            plan[school][1][w].add(urls[a]); n[f'{school}:lane_bulk'] += 1
        else:
            n[f'{school}:lane_not_in_bulk'] += 1
    return rows


def write(school, rows, stamp, dry):
    rows = list({(r['work_id'], r['url']): r for r in rows}.values())
    works = len({r['work_id'] for r in rows})
    if dry or not rows:
        return dict(rows=len(rows), works=works, written=False)
    rule = __doc__
    if school == 'princeton':
        pkg = FT / 'princeton' / 'discovery' / f'claude-study-copies-{stamp}'
        (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
        ev = pkg / 'evidence' / 'study-copies.json'
        ev.write_text(json.dumps(dict(rule=rule, created_at=datetime.now(timezone.utc).isoformat(), rows=rows)))
        with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
            for r in rows:
                f.write(json.dumps(dict(work_id=r['work_id'], url=r['url'], landing_url=r['landing_url'], license=None, version=r['version'],
                                        metadata_source=str(ev), source=r['source'], detail=r['detail'])) + '\n')
        (pkg / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in rows)) + '\n')
        (pkg / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(Counter(r['source'] for r in rows)),
                                                          works_gaining_candidate=works, requires_packages=[], rules=rule), indent=1))
        return dict(rows=len(rows), works=works, package=str(pkg))
    ev = FT / school / 'discovery' / f'claude-{school}-catalog' / 'evidence' / f'study-copies-{stamp}.json'
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text(json.dumps(dict(rule=rule, created_at=datetime.now(timezone.utc).isoformat(), rows=rows)))
    db = sqlite3.connect(str(FT / school / 'catalog.sqlite'), timeout=300)
    added = 0
    for attempt in range(20):  # the collector writes to the same catalog: wait out its locks
        try:
            added = sum(db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',
                                   (r['work_id'], r['url'], r['landing_url'], None, r['version'], str(ev))).rowcount for r in rows)
            db.commit(); break
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(30)
    return dict(rows=len(rows), works=works, candidates_added=added, evidence=str(ev))


def main():
    args = sys.argv[1:]
    dry = '--dry' in args
    schools = ['princeton', 'cmu', 'epfl', 'mit']
    if '--schools' in args:
        schools = args[args.index('--schools') + 1].split(',')
    ALL = ('arxiv', 'lane', 's2', 'openalex', 'core', 'figshare', 'pmc')
    steps = [a for a in args if a in ALL] or list(ALL)
    corpus = defaultdict(list)
    for line in gzip.open(STAGE / 'corpus' / 'papers.jsonl.gz', 'rt'):
        r = json.loads(line)
        if r['school'] in schools:
            corpus[r['school']].append(r)
    plan = {}
    for school in schools:
        plan[school] = missing(school, corpus[school])
        print(json.dumps(dict(school=school, study=len(corpus[school]), missing=len(plan[school][0]))), flush=True)
    n = Counter(); rows = defaultdict(list)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    if 'arxiv' in steps:
        for school, rs in arxiv_rows(plan, n).items():
            rows[school] += rs
            for r in rs:
                plan[school][1][r['work_id']].add(r['url'])
        print(json.dumps(dict(after='arxiv', counts=dict(n), rows={s: len(v) for s, v in rows.items()})), flush=True)
        for school in schools:  # write now: the S2 step takes longer
            print(json.dumps(dict(school=school, step='arxiv', **write(school, rows.pop(school, []), stamp + 'a', dry))), flush=True)
    if 'lane' in steps:
        for school, rs in lane_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='lane', counts=dict(n))), flush=True)
        for school in schools:
            print(json.dumps(dict(school=school, step='lane', **write(school, rows.pop(school, []), stamp + 'l', dry))), flush=True)
    if 's2' in steps:
        for school, rs in s2_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='s2', counts=dict(n))), flush=True)
        for school in schools:
            for r in rows.get(school, []):
                plan[school][1][r['work_id']].add(r['url'])
            print(json.dumps(dict(school=school, step='s2', **write(school, rows.pop(school, []), stamp + 's', dry))), flush=True)
    if 'openalex' in steps:
        for school, rs in openalex_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='openalex', counts=dict(n))), flush=True)
        for school in schools:
            print(json.dumps(dict(school=school, step='openalex', **write(school, rows.pop(school, []), stamp + 'o', dry))), flush=True)
    if 'pmc' in steps:
        for school, rs in pmc_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='pmc', counts=dict(n))), flush=True)
        for school in schools:
            print(json.dumps(dict(school=school, step='pmc', **write(school, rows.pop(school, []), stamp + 'p', dry))), flush=True)
    if 'figshare' in steps:
        for school, rs in figshare_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='figshare', counts=dict(n))), flush=True)
        for school in schools:
            print(json.dumps(dict(school=school, step='figshare', **write(school, rows.pop(school, []), stamp + 'f', dry))), flush=True)
    if 'core' in steps:
        for school, rs in core_rows(plan, n).items():
            rows[school] += rs
        print(json.dumps(dict(after='core', counts=dict(n))), flush=True)
        for school in schools:
            print(json.dumps(dict(school=school, step='core', **write(school, rows.pop(school, []), stamp + 'c', dry))), flush=True)


if __name__ == '__main__':
    main()
