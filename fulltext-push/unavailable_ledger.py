"""The unavailability ledger (2026-10-30, owner; the standard is docs/UNAVAILABLE.md): for every CS lab paper without a
local copy, one record with a reason code from a fixed vocabulary, a one-sentence summary, the publisher and venue, every
applicable open source's dated check, and every download attempt.

usage: unavailable_ledger.py <school> [<school> ...] [--max-age-days N] [--offline] [--only <paper key>]
                             [--no-network-sources s2_title,wayback_acm,...]
  reads   hierarchy/<school>/copies.json (tools/lab_paper_copies.py; the non-local papers), the lab papers, the
          school's catalog (read-only, short chunks: works through the works_slim index, candidates, attempts), the
          channels' caches and the checks store (fulltext-push/checks/<school>.sqlite, checks.py)
  asks    only checks that are missing, stale (older than N days, OpenAlex 7) or asked with another query; with the
          existing per-host pacing: OpenAlex 50 ids per request (budget-guarded, oa_refresh.get), S2 /paper/batch 500 ids
          per request and /paper/search/match (s2_key_lookup.s2: one request per 1.2 s across processes), CORE 25 DOIs
          per request, NCBI ID converter 200 ids per request, PMC open-data listing, Wayback CDX one per 8 s, Crossref
          prefixes one per s; never a page fetch, never the owner's email
  writes  hierarchy/<school>/unavailable.jsonl.gz and unavailable-summary.json, the new checks into the checks store,
          and the reason onto copies.json (lab_paper_copies.attach_ledger). Catalogs are never written.
"""
import argparse, difflib, gzip, json, os, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402
import checks as C  # noqa: E402

RAW = F.P.FT_RAW
MAX_AGE = 30.0
OA_AGE = 7.0
UA = F.UA

# ---------------------------------------------------------------- vocabulary (docs/UNAVAILABLE.md)
REASONS = {  # code: final?
    'found_awaiting_download': False, 'found_not_in_catalog': False, 'pending_retry': False, 'incomplete_check': False,
    'identity_unconfirmed': False, 'open_copy_bot_challenge': True, 'open_copy_behind_login': True, 'open_copy_robots_disallowed': True,
    'landing_page_without_pdf': True, 'open_copy_unusable': True, 'paywall_only': True, 'publisher_only_closed': True,
    'no_doi_no_match': True}
SOURCES = ['openalex', 'arxiv', 's2', 'core', 'pmc', 'dblp', 'proceedings', 'repository', 'labpages', 'wayback_acm']
LABEL = dict(openalex='OpenAlex', arxiv='arXiv', s2='Semantic Scholar', core='CORE', pmc='PubMed Central', dblp='DBLP links',
             proceedings='the open proceedings', repository='the school repository', labpages="the PI's lab and home pages",
             wayback_acm='the Wayback Machine (ACM PDF)')
REPO = dict(princeton='Princeton OAR', mit='DSpace@MIT Open Access Articles', cmu='KiltHub', epfl='Infoscience',
            berkeley='eScholarship (through OpenAlex and CORE)', stanford='the Stanford Digital Repository (through OpenAlex and CORE)',
            michigan='Deep Blue Documents (never asked; through OpenAlex and CORE)')
PUBFOLD = [(r'Institute of Electrical and Electronics Engineers|\bIEEE\b', 'IEEE'), (r'Association for Computing Machinery|\bACM\b', 'ACM'),
           (r'Springer|Nature Portfolio|Nature Publishing|BioMed Central|Palgrave', 'Springer Nature'), (r'\bSSRN\b|Social Science Research Network|RELX', 'SSRN (Elsevier)'),
           (r'Elsevier|Cell Press|Academic Press|North-Holland|Pergamon', 'Elsevier'), (r'Wiley|Blackwell', 'Wiley'),
           (r'Taylor ?(&|and) ?Francis|Routledge|Informa', 'Taylor & Francis'), (r'Optica|Optical Society', 'Optica'), (r'\bSPIE\b', 'SPIE'),
           (r'SAGE', 'SAGE'), (r'Oxford University Press', 'Oxford University Press'), (r'Cambridge University Press', 'Cambridge University Press'),
           (r'American Physical Society', 'APS'), (r'American Chemical Society', 'ACS'), (r'Institute of Physics|IOP Publishing', 'IOP'),
           (r'AIP Publishing|American Institute of Physics', 'AIP'), (r'Society for Industrial and Applied Mathematics|\bSIAM\b', 'SIAM'),
           (r'INFORMS|Institute for Operations Research', 'INFORMS'), (r'MIT Press', 'MIT Press'), (r'De Gruyter', 'De Gruyter'),
           (r'World Scientific', 'World Scientific'), (r'Emerald', 'Emerald'), (r'IOS Press', 'IOS Press'), (r'American Association for the Advancement of Science|\bAAAS\b', 'AAAS'),
           (r'Proceedings of the National Academy|National Academy of Sciences', 'PNAS'), (r'Mary Ann Liebert', 'Mary Ann Liebert'),
           (r'Annual Reviews', 'Annual Reviews'), (r'Now Publishers', 'now publishers'), (r'Inderscience', 'Inderscience'), (r'IGI Global', 'IGI Global')]
PREFIX_PUB = {'10.1109': 'IEEE', '10.1145': 'ACM', '10.1007': 'Springer Nature', '10.1038': 'Springer Nature', '10.1016': 'Elsevier',
              '10.2139': 'SSRN (Elsevier)', '10.1002': 'Wiley', '10.1111': 'Wiley', '10.1080': 'Taylor & Francis', '10.1364': 'Optica',
              '10.1117': 'SPIE', '10.1177': 'SAGE', '10.1093': 'Oxford University Press', '10.1017': 'Cambridge University Press',
              '10.1103': 'APS', '10.1021': 'ACS', '10.1088': 'IOP', '10.1063': 'AIP', '10.1137': 'SIAM', '10.1287': 'INFORMS',
              '10.1162': 'MIT Press', '10.1126': 'AAAS', '10.1073': 'PNAS', '10.3233': 'IOS Press', '10.1561': 'now publishers',
              '10.48550': 'arXiv', '10.23919': 'IEEE', '10.1049': 'IET', '10.1115': 'ASME', '10.1061': 'ASCE', '10.1142': 'World Scientific',
              '10.1515': 'De Gruyter', '10.1108': 'Emerald', '10.4018': 'IGI Global', '10.1504': 'Inderscience', '10.3390': 'MDPI',
              '10.3389': 'Frontiers', '10.1371': 'PLOS', '10.1186': 'Springer Nature', '10.1101': 'Cold Spring Harbor Laboratory (bioRxiv)'}


def now():
    return datetime.now(timezone.utc).isoformat()


def host(u):
    return (urlsplit(u or '').hostname or '').lower()


def fold_publisher(name):
    for pat, short in PUBFOLD:
        if name and re.search(pat, name, re.I):
            return short
    return name or None


def jdump(path, rows):
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.part')
    with gzip.open(tmp, 'wt') as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + '\n')
    os.replace(tmp, path)


def read_jsonl(p, key):
    out = {}
    if Path(p).exists():
        with open(p) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                k = key(r)
                if k is not None:
                    out[k] = r
    return out


def check(source, query, result, detail=None, at=None):
    return dict(source=source, at=at or now(), query=query, result=result, detail=detail)


# ---------------------------------------------------------------- papers and catalog state

def load_school(school):
    """The non-local lab papers by copies.json, with their catalog group, attempts and untried candidates."""
    copies = json.loads((F.P.data('copies.json', school)).read_text())
    rows = F.lab_papers(school)
    papers = {}
    for k, c in copies['papers'].items():
        if c.get('status') in F.LOCAL:
            continue
        r = rows.get(k)
        if r is None:
            continue
        papers[k] = dict(key=k, school=school, r=r, cid=c.get('catalog'), status=c.get('status'), doi=F.ndoi(r.get('doi')) or None,
                         access=dict(verdict=c.get('access_verdict'), cause=c.get('access_cause')) if c.get('access_verdict') or c.get('access_cause') else None)
    cat = F.FT / school / 'catalog.sqlite'
    if not cat.exists():
        for p in papers.values():
            p.update(group=[], attempts=[], cands=set())
        return papers
    want_doi = {p['doi'] for p in papers.values() if p['doi']}
    want_t = {F.nt(p['r'].get('title')) for p in papers.values()} - {''}
    db = sqlite3.connect(f'file:{cat}?mode=ro', uri=True, timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    doi_ids, t_ids, st = defaultdict(list), defaultdict(list), {}
    for i, d, s, t in F.works_rows(db, 'id, doi, status, title'):
        st[i] = s
        d = F.ndoi(d)
        if d in want_doi:
            doi_ids[d].append(i)
        k = F.nt(t)
        if len(k) >= 20 and k in want_t:
            t_ids[k].append(i)
    gid = defaultdict(set)
    for k, p in papers.items():
        g = ([p['cid']] if p['cid'] else []) + doi_ids.get(p['doi'], []) + t_ids.get(F.nt(p['r'].get('title')), [])
        p['group'] = [i for i in dict.fromkeys(g) if st.get(i) not in F.LOCAL]
        p['quarantined'] = any(st.get(i) == 'quarantined_robots_ai' for i in p['group'])  # quarantine_robots_ai.py (2026-10-31)
        for i in p['group']:
            gid[i].add(k)
    att, cand = defaultdict(list), defaultdict(set)
    for w, u, at, s, d in F.chunks(db, 'attempts', 'work_id, url, observed_at, status, detail', n=20000):
        if w in gid:
            att[w].append(dict(url=u, at=at, status=s, detail=(d or '')[:400]))
    for w, u in F.chunks(db, 'candidates', 'work_id, url', n=20000):
        if w in gid:
            cand[w].add(u)
    db.close()
    if school == 'princeton':  # candidates waiting in discovery packages (imported at the Princeton stage's own pace)
        for f in sorted((F.FT / 'princeton' / 'discovery').glob('claude-*/*candidates.jsonl')):
            with open(f) as fh:
                for line in fh:
                    try:
                        c = json.loads(line)
                    except ValueError:
                        continue
                    if c.get('work_id') in gid:
                        cand[c['work_id']].add(c['url'])
    from review_access import cause
    for p in papers.values():
        p['attempts'] = sorted([dict(a, work_id=w, cause=cause(dict(url=a['url'], status=a['status'], detail=a['detail']))[0])
                                for w in p['group'] for a in att.get(w, [])], key=lambda a: a['at'] or '')
        p['cands'] = set().union(*[cand.get(w, set()) for w in p['group']]) if p['group'] else set()
        tried = {a['url'] for a in p['attempts']}
        p['untried'] = sorted(p['cands'] - tried)
        p['all_urls'] = p['cands'] | tried
    return papers


# ---------------------------------------------------------------- sources

def oa_detail(b):
    oa = b.get('open_access') or {}
    pl = b.get('primary_location') or {}
    src = pl.get('source') or {}
    locs = []
    for l in b.get('locations') or []:
        s = l.get('source') or {}
        locs.append(dict(host=host(l.get('landing_page_url') or l.get('pdf_url')), landing=l.get('landing_page_url'), pdf=l.get('pdf_url'),
                         version=l.get('version'), is_oa=l.get('is_oa'), type=s.get('type'), source=s.get('display_name')))
    try:
        rows, pmc = F.oa_location_rows('x', b)
    except Exception:
        rows, pmc = [], set()
    arx = F.arxiv_of({}, b)
    usable = [r['url'] for r in rows] + (['arXiv:' + arx] if arx else []) + ['PMC' + p for p in sorted(pmc)]
    ids = b.get('ids') or {}
    return dict(is_oa=oa.get('is_oa'), oa_status=oa.get('oa_status'), oa_url=oa.get('oa_url'), locations=locs[:20], usable=usable, arxiv=arx,
                pmcids=sorted(pmc) + ([str(ids['pmcid']).rsplit('/', 1)[-1].replace('PMC', '')] if ids.get('pmcid') else []),
                pmid=str(ids['pmid']).rsplit('/', 1)[-1] if ids.get('pmid') else None, venue=src.get('display_name'), venue_type=src.get('type'),
                publisher=src.get('host_organization_name') or ((src.get('host_organization_lineage_names') or [None])[0]),
                doi=F.ndoi(b.get('doi')) or None, title=b.get('title'))


def src_openalex(papers, offline, n):
    """OpenAlex records, 50 ids per request (filter=openalex_id:..), select with open_access; cache raw/ledger_openalex.jsonl."""
    cache_f = RAW / 'ledger_openalex.jsonl'
    cache = read_jsonl(cache_f, lambda r: r.get('id'))
    isw = lambda i: bool(re.match(r'https://openalex\.org/W\d+$', i or ''))  # lab papers from DBLP or lab pages carry their own keys
    want = list(dict.fromkeys(p['r']['oa'] for p in papers if isw(p['r'].get('oa'))))
    stale = [i for i in want if i not in cache or C.age_days(cache[i].get('at')) > OA_AGE]
    n['openalex_to_ask'] = 0 if offline else len(stale)
    if stale and not offline:
        # single-work requests: OpenAlex charges list requests against the key's daily credits (one per request) but
        # not single-work GETs (X-RateLimit-Credits-Used 0, 2026-10-30); one request per 0.15 s as fetch_oa_bodies,
        # 429 backs off. Every request is logged with the others in raw/openalex_budget.jsonl.
        import requests
        s = requests.Session(); s.headers['User-Agent'] = UA
        key = os.environ.get('OPENALEX_API_KEY', '')
        sel = 'id,doi,title,publication_year,ids,open_access,primary_location,locations,best_oa_location'
        with cache_f.open('a') as f, (RAW / 'openalex_budget.jsonl').open('a') as blog:
            for k, i in enumerate(stale):
                for attempt in range(5):
                    time.sleep(0.15)
                    try:
                        r = s.get('https://api.openalex.org/works/' + F.oa_short(i), params=dict(select=sel, **({'api_key': key} if key else {})), timeout=(15, 60))
                    except Exception:
                        time.sleep(20); continue
                    if r.status_code == 429:
                        blog.write(json.dumps(dict(at=now(), kind='ledger_single', status=429, remaining=r.headers.get('X-RateLimit-Remaining'))) + '\n')
                        time.sleep(60 * (attempt + 1)); continue
                    break
                else:
                    n['openalex_failed'] += 1; continue
                if k % 500 == 0:
                    blog.write(json.dumps(dict(at=now(), kind='ledger_single', status=r.status_code, credits=r.headers.get('X-RateLimit-Credits-Used'),
                                               remaining=r.headers.get('X-RateLimit-Remaining'))) + '\n'); blog.flush()
                if r.status_code == 200:
                    b = r.json()
                    x = dict(id=i, at=now(), body=b, canonical=b.get('id'))
                elif r.status_code == 404:
                    x = dict(id=i, at=now(), body=None, gone=True)
                else:
                    n['openalex_failed'] += 1; continue
                cache[i] = x; f.write(json.dumps(x) + '\n')
                if k % 100 == 99:
                    f.flush()
                if k % 2000 == 1999:
                    print(json.dumps(dict(openalex_asked=k + 1, of=len(stale))), flush=True)
    out = {}
    for p in papers:
        i = p['r'].get('oa')
        x = cache.get(i)
        if not isw(i):
            out[p['key']] = check('openalex', i, 'not_applicable', 'no OpenAlex work: the lab paper comes from DBLP or a lab page'); continue
        if not x or C.age_days(x.get('at')) > OA_AGE:
            out[p['key']] = check('openalex', F.oa_short(i), 'error', 'record not refreshed within 7 days', at=(x or {}).get('at')); continue
        if not x.get('body'):
            out[p['key']] = check('openalex', F.oa_short(i), 'error', 'the API returned no record for this id (merged or deleted)', at=x['at']); continue
        d = oa_detail(x['body'])
        out[p['key']] = check('openalex', F.oa_short(i), 'found' if d['usable'] else 'none', d, at=x['at'])
    return out


def s2_ids(p, oa):
    if p['doi'] and not p['doi'].startswith('10.48550/'):
        return 'DOI:' + p['doi']
    a = arxiv_known(p, oa)
    if a:
        return 'ARXIV:' + a
    return None


def arxiv_known(p, oa=None):
    """An arXiv id from the paper's own identifiers: its 10.48550 DOI, the hierarchy's arxiv field, an edition's DOI, OpenAlex."""
    r = p['r']
    for d in [r.get('doi')] + [e.get('doi') for e in r.get('editions') or []]:
        d = F.ndoi(d)
        if d.startswith('10.48550/arxiv.'):
            return d.split('arxiv.', 1)[1]
    if r.get('arxiv'):
        return re.sub(r'v\d+$', '', r['arxiv'])
    if oa and oa.get('detail') and isinstance(oa['detail'], dict) and oa['detail'].get('arxiv'):
        return oa['detail']['arxiv']
    return None


def src_s2(papers, oa, offline, n, title_max=None):
    os.environ.setdefault('S2_BATCH_ONLY', '1')
    import s2_key_lookup as s2k
    cache = read_jsonl(s2k.CACHE, lambda r: r.get('id'))
    ids, titles = {}, {}
    for p in papers:
        i = s2_ids(p, oa.get(p['key']))
        if i:
            ids[p['key']] = i
        elif len(F.nt(p['r'].get('title'))) >= 20:
            titles[p['key']] = 'match:' + s2k.nt(p['r']['title'])
    fresh = lambda i: i in cache and not cache[i].get('error') and C.age_days(cache[i].get('at')) <= MAX_AGE
    todo = [i for i in dict.fromkeys(ids.values()) if not fresh(i)]
    tt = [p['r']['title'] for p in papers if p['key'] in titles and not fresh(titles[p['key']])]
    tt = list(dict.fromkeys(tt))[:title_max] if title_max is not None else list(dict.fromkeys(tt))
    n['s2_batch_to_ask'], n['s2_titles_to_ask'] = len(todo), len(tt)
    if (todo or tt) and not offline:
        import requests
        F.load_env()
        s = requests.Session(); s.headers['x-api-key'] = os.environ['S2_API_KEY']; s.headers['User-Agent'] = UA
        with s2k.CACHE.open('a') as f:
            for i in range(0, len(todo), 500):
                chunk = todo[i:i + 500]
                r = s2k.s2(s, 'POST', '/paper/batch', params={'fields': s2k.FIELDS}, json={'ids': chunk})
                res = r.json() if r is not None and r.status_code == 200 else None
                for k, lid in enumerate(chunk):
                    rec = dict(id=lid, at=now(), data=res[k]) if res is not None else dict(id=lid, at=now(), error=r.status_code if r is not None else 'failed')
                    cache[lid] = rec; f.write(json.dumps(rec) + '\n')
                f.flush()
            fails = 0
            for k, title in enumerate(tt):
                r = s2k.s2(s, 'GET', '/paper/search/match', params={'query': title, 'fields': s2k.FIELDS})
                lid = 'match:' + s2k.nt(title)
                if r is None or r.status_code not in (200, 404, 400):
                    rec = dict(id=lid, at=now(), error=r.status_code if r is not None else 'failed'); fails += 1
                else:
                    rec = dict(id=lid, at=now(), data=(r.json().get('data') or [None])[0] if r.status_code == 200 else None); fails = 0
                cache[lid] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
                if fails >= 15:
                    n['s2_title_stopped'] = k + 1; break
    out = {}
    for p in papers:
        lid = ids.get(p['key']) or titles.get(p['key'])
        if not lid:
            out[p['key']] = check('s2', None, 'not_applicable', 'no DOI, no arXiv id and a title under 20 characters'); continue
        rec = cache.get(lid)
        if not rec or rec.get('error') or C.age_days(rec.get('at')) > MAX_AGE:
            out[p['key']] = check('s2', lid, 'error', f"no fresh answer ({(rec or {}).get('error') or 'not asked'})", at=(rec or {}).get('at')); continue
        d = rec.get('data')
        if not d:
            out[p['key']] = check('s2', lid, 'none', 'Semantic Scholar has no record for this id' if not lid.startswith('match:') else 'no title match', at=rec['at']); continue
        if lid.startswith('match:'):
            fams = {s2k.family(a.get('name') or '') for a in d.get('authors') or []}
            people = list(p['r'].get('byline') or []) + list(p['r'].get('pis') or [])
            y = p['r'].get('year')
            if s2k.nt(d.get('title') or '') != s2k.nt(p['r']['title']) or not fams & {s2k.family(x) for x in people} or (y and d.get('year') and abs(y - d['year']) > 2):
                out[p['key']] = check('s2', lid, 'none', dict(rejected_match=d.get('title'), year=d.get('year')), at=rec['at']); continue
        ext = d.get('externalIds') or {}
        pdf = (d.get('openAccessPdf') or {}).get('url') or ''
        usable = []
        if ext.get('ArXiv'):
            usable.append('arXiv:' + ext['ArXiv'])
        if ext.get('PubMedCentral'):
            usable.append('PMC' + str(ext['PubMedCentral']))
        if ext.get('ACL'):
            usable.append(f"https://aclanthology.org/{ext['ACL']}.pdf")
        if pdf and s2k.ok_pdf(pdf):
            usable.append(pdf)
        det = dict(externalIds={k: ext.get(k) for k in ('ArXiv', 'PubMedCentral', 'PubMed', 'ACL', 'DOI') if ext.get(k)}, openAccessPdf=pdf or None,
                   openAccessPdf_unusable_host=bool(pdf and not s2k.ok_pdf(pdf)), usable=usable, title=d.get('title'))
        out[p['key']] = check('s2', lid, 'found' if usable else 'none', det, at=rec['at'])
    return out


def src_core(papers, offline, n):
    import core_search as cs
    cache = read_jsonl(cs.CACHE, lambda r: r.get('doi'))
    dois = {p['key']: p['doi'] for p in papers if p['doi'] and not p['doi'].startswith('10.48550/')}
    fresh = lambda d: d in cache and not cache[d].get('error') and C.age_days(cache[d].get('at')) <= MAX_AGE
    todo = [d for d in dict.fromkeys(dois.values()) if not fresh(d) and '"' not in d and '\\' not in d]
    n['core_to_ask'] = len(todo)
    if todo and not offline:
        import requests
        F.load_env()
        s = requests.Session(); s.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']; s.headers['User-Agent'] = UA
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
                at = now()
                for d in chunk:
                    rec = dict(doi=d, at=at, links=list(dict.fromkeys(got.get(d, [])))) if res is not None else dict(doi=d, at=at, error=True)
                    cache[d] = rec; f.write(json.dumps(rec) + '\n')
                f.flush()
                if (i // 25) % 40 == 39:
                    print(json.dumps(dict(core_asked=i + len(chunk), of=len(todo))), flush=True)
    out = {}
    for p in papers:
        d = dois.get(p['key'])
        if not d:
            out[p['key']] = check('core', None, 'not_applicable', 'no DOI'); continue
        rec = cache.get(d)
        if not fresh(d):
            out[p['key']] = check('core', 'doi:' + d, 'error', 'no fresh answer', at=(rec or {}).get('at')); continue
        links = rec.get('links') or []
        usable = [u for u in links if cs.usable(u)]
        out[p['key']] = check('core', 'doi:' + d, 'found' if usable else 'none', dict(links=links[:8], usable=usable[:5]), at=rec['at'])
    return out


def src_pmc(papers, oa, s2, offline, n):
    """PubMed Central where the paper has a PubMed / PMC identifier: PMID -> PMCID (NCBI ID converter, 200 per request),
    PMCID -> its files in the PMC open-data dataset on S3. Europe PMC's cached DOI answers add identifiers."""
    import europepmc_lookup as ep
    epmc = read_jsonl(ep.CACHE, lambda r: r.get('doi'))
    conv_f, s3_f = RAW / 'ledger_idconv.jsonl', RAW / 'ledger_pmc_s3.jsonl'
    conv = read_jsonl(conv_f, lambda r: r.get('pmid'))
    s3 = read_jsonl(s3_f, lambda r: r.get('pmcid'))
    ids = {}
    for p in papers:
        pmids, pmcids = set(), set()
        od = (oa.get(p['key']) or {}).get('detail')
        if isinstance(od, dict):
            if od.get('pmid'):
                pmids.add(od['pmid'])
            pmcids |= set(od.get('pmcids') or [])
        sd = (s2.get(p['key']) or {}).get('detail')
        if isinstance(sd, dict):
            e = sd.get('externalIds') or {}
            if e.get('PubMed'):
                pmids.add(str(e['PubMed']))
            if e.get('PubMedCentral'):
                pmcids.add(str(e['PubMedCentral']))
        for u in p['all_urls']:
            m = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', u)
            if m:
                pmids.add(m.group(1))
            m = F.PMC_LINK.search(u)
            if m:
                pmcids.add(m.group(1))
        e = epmc.get(p['doi'] or '')
        if e and not e.get('error'):
            if e.get('pmid'):
                pmids.add(str(e['pmid']))
            if e.get('pmcid'):
                pmcids.add(str(e['pmcid']).replace('PMC', ''))
        pmcids = {re.sub(r'\D', '', x) for x in pmcids if re.sub(r'\D', '', x)}
        if pmids or pmcids:
            ids[p['key']] = (pmids, pmcids)
    fresh = lambda rec: rec and not rec.get('error') and C.age_days(rec.get('at')) <= MAX_AGE
    todo = sorted({m for pm, pc in ids.values() for m in pm if not fresh(conv.get(m))})
    n['pmc_idconv_to_ask'] = len(todo)
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    if todo and not offline:
        with conv_f.open('a') as f:
            for i in range(0, len(todo), 200):
                part = todo[i:i + 200]
                time.sleep(3)
                try:
                    r = s.get('https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/', params=dict(ids=','.join(part), format='json'), timeout=(15, 60))
                    recs = {str(x.get('pmid') or x.get('requested-id')): x for x in r.json().get('records', [])} if r.status_code == 200 else None
                except Exception:
                    recs = None
                for m in part:
                    x = (recs or {}).get(m)
                    rec = dict(pmid=m, at=now(), pmcid=(x or {}).get('pmcid')) if recs is not None else dict(pmid=m, at=now(), error=True)
                    conv[m] = rec; f.write(json.dumps(rec) + '\n')
                f.flush()
    for pm, pc in ids.values():
        for m in pm:
            c = conv.get(m)
            if c and c.get('pmcid'):
                pc.add(re.sub(r'\D', '', c['pmcid']))
    todo = sorted({c for pm, pc in ids.values() for c in pc if not fresh(s3.get(c))})
    n['pmc_s3_to_ask'] = len(todo)
    if todo and not offline:
        import s2_key_lookup as s2k
        with s3_f.open('a') as f:
            for c in todo:
                files = s2k.pmc_files(s, c, {})
                rec = dict(pmcid=c, at=now(), files=files)
                s3[c] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
    out = {}
    for p in papers:
        if p['key'] not in ids:
            out[p['key']] = check('pmc', None, 'not_applicable', 'no PubMed or PMC identifier in OpenAlex, Semantic Scholar, Europe PMC or the known links'); continue
        pm, pc = ids[p['key']]
        q = dict(pmid=sorted(pm), pmcid=sorted(pc))
        if any(not fresh(conv.get(m)) for m in pm) or any(not fresh(s3.get(c)) for c in pc):
            out[p['key']] = check('pmc', q, 'error', 'identifier conversion or PMC listing not done'); continue
        files = [u for c in pc for u in s3[c].get('files') or []]
        det = dict(files=files[:4], usable=files[:4]) if files else \
            dict(note='in PMC but not in the open-access dataset (PMC terms do not allow redistribution)' if pc else 'PMID not in PubMed Central (abstract only)')
        out[p['key']] = check('pmc', q, 'found' if files else 'none', det, at=max([conv[m]['at'] for m in pm] + [s3[c]['at'] for c in pc]))
    return out


def src_dblp(by_school, offline, n):
    """DBLP dump records matched by DOI or title + author family + year (dblp_ee.scan), one streaming pass for every
    school's papers that lack a fresh scan; matches raw/ledger_dblp_<school>.jsonl.gz, scanned keys beside it."""
    import dblp_ee
    need = {}
    for school, papers in by_school.items():
        side = RAW / f'ledger_dblp_{school}.json'
        sc = json.loads(side.read_text()) if side.exists() else {}
        keys = set(sc.get('keys') or [])
        if any(p['key'] not in keys for p in papers) or C.age_days(sc.get('at')) > MAX_AGE:
            need[school] = papers
    n['dblp_scan_schools'] = len(need)
    if need and not offline:
        extra = [dict(key=f"{s}|{p['key']}", doi=p['r'].get('doi'), editions=[e.get('doi') for e in p['r'].get('editions') or [] if e.get('doi')],
                      title=p['r'].get('title'), year=p['r'].get('year'), byline=p['r'].get('byline'), pis=p['r'].get('pis'))
                 for s, ps in need.items() for p in ps]
        tmp = RAW / 'ledger_dblp_scan.jsonl.gz'
        dblp_ee.scan(extra, out=tmp, only_extra=True)
        at = now()
        per = defaultdict(list)
        for l in gzip.open(tmp, 'rt'):
            x = json.loads(l)
            s, k = x['paper'].split('|', 1)
            per[s].append(dict(x, paper=k))
        for s, ps in need.items():
            jdump(RAW / f'ledger_dblp_{s}.jsonl.gz', per.get(s, []))
            (RAW / f'ledger_dblp_{s}.json').write_text(json.dumps(dict(at=at, dump=str(dblp_ee.DUMP), keys=[p['key'] for p in ps])))
    out = defaultdict(dict)
    for school, papers in by_school.items():
        side = RAW / f'ledger_dblp_{school}.json'
        sc = json.loads(side.read_text()) if side.exists() else {}
        keys = set(sc.get('keys') or [])
        recs = defaultdict(list)
        mf = RAW / f'ledger_dblp_{school}.jsonl.gz'
        if mf.exists():
            for l in gzip.open(mf, 'rt'):
                x = json.loads(l); recs[x['paper']].append(x)
        dump = Path(sc.get('dump') or '').name
        for p in papers:
            q = p['doi'] or p['r'].get('title')
            if p['key'] not in keys:
                out[school][p['key']] = check('dblp', q, 'error', 'not scanned'); continue
            xs = recs.get(p['key'], [])
            ees = [e for x in xs for e in x['ee']]
            opn = [u for e in ees if (u := dblp_ee.open_url(e))]
            a = dblp_ee.arxiv_from(ees)
            usable = opn + (['arXiv:' + a] if a else [])
            det = dict(dump=dump, records=[x['dblp_key'] for x in xs][:6], ee=ees[:8], usable=usable[:5]) if xs else dict(dump=dump, records=[], note='no DBLP record matched by DOI or title + author + year')
            out[school][p['key']] = check('dblp', q, 'found' if usable else 'none', det, at=sc.get('at'))
    return out


def src_proceedings(papers, n):
    import s2_key_lookup as s2k
    src = F.P.archive_sweep('claude-princeton-20261015') / 'cs-structure/raw/proceedings/index.json.gz'
    idx = defaultdict(list)
    for t, y, u, land, venue in json.loads(gzip.decompress(src.read_bytes())):
        k = F.nt(t)
        if len(k) >= 20:
            idx[k].append((y, u, land, venue))
    built = datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).date().isoformat()
    out = {}
    for p in papers:
        k = F.nt(p['r'].get('title'))
        if len(k) < 20:
            out[p['key']] = check('proceedings', None, 'not_applicable', 'title under 20 characters'); continue
        y0 = p['r'].get('year')
        hits = [(y, u, venue) for y, u, land, venue in idx.get(k, []) if (not y0 or not y or abs(int(y) - int(y0)) <= 2) and s2k.ok_pdf(u)]
        out[p['key']] = check('proceedings', p['r']['title'][:200], 'found' if hits else 'none',
                              dict(usable=[u for _, u, _ in hits][:3], venues=[v for _, _, v in hits][:3], index_built=built) if hits else dict(index_built=built, entries=sum(map(len, idx.values()))))
    return out


def src_repository(school, papers, oa, core, offline, n):
    """The school's open-access repository, from the harvested indexes (nothing is fetched except unresolved Infoscience
    handles through its REST API, as the infoscience step does)."""
    out = {}
    tkey = lambda t: F.nt(t) if len(F.nt(t)) >= 30 else None
    if school == 'princeton':
        import glob
        by_doi, by_t, items = {}, {}, 0
        for f in sorted(glob.glob(str(F.P.archive_sweep('claude-princeton-20261015') / 'cs-structure/raw/oar/items_*.json.gz'))):
            for it in json.loads(gzip.open(f).read()):
                if it.get('status') != 200:
                    continue
                items += 1
                for d in it.get('dois') or []:
                    by_doi.setdefault(F.ndoi(d), it)
                if tkey(it.get('title')):
                    by_t.setdefault(tkey(it['title']), it)
        for p in papers:
            it = by_doi.get(p['doi'] or '') or by_t.get(tkey(p['r'].get('title')) or '')
            if it:
                out[p['key']] = check('repository', p['doi'] or p['r'].get('title'), 'found' if it.get('pdf') else 'none',
                                      dict(repository='Princeton OAR', item=it.get('url'), pdf=it.get('pdf'), note=None if it.get('pdf') else 'OAR item without a file'))
            else:
                out[p['key']] = check('repository', p['doi'] or p['r'].get('title'), 'none', dict(repository='Princeton OAR', items_indexed=items, note='no OAR item with this DOI or title'))
        return out
    if school == 'mit':
        import mit_oa_articles as moa
        complete = (RAW / 'mit_oa_articles.done').exists()
        by_doi, by_t, k = {}, {}, 0
        for it in moa.items():
            k += 1
            for d in it['dois']:
                by_doi.setdefault(d, it)
            for t in it['titles']:
                if tkey(t):
                    by_t.setdefault(tkey(t), it)
        for p in papers:
            it = by_doi.get(p['doi'] or '') or by_t.get(tkey(p['r'].get('title')) or '')
            q = p['doi'] or p['r'].get('title')
            if it:
                out[p['key']] = check('repository', q, 'found', dict(repository='DSpace@MIT Open Access Articles', usable=[f"https://hdl.handle.net/1721.1/{it['handle']}"]))
            elif complete:
                out[p['key']] = check('repository', q, 'none', dict(repository='DSpace@MIT Open Access Articles', items_indexed=k))
            else:
                out[p['key']] = check('repository', q, 'error', dict(repository='DSpace@MIT Open Access Articles', note=f'harvest partial ({k} items)'))
        return out
    if school == 'cmu':
        lst = json.loads((F.P.archive_sweep('claude-cmu-20261017') / 'raw/kilthub/list.json').read_text())
        by_doi, by_t = {}, {}
        for it in lst['items']:
            if it.get('doi'):
                by_doi.setdefault(F.ndoi(it['doi']), it)
            if tkey(it.get('title')):
                by_t.setdefault(tkey(it['title']), it)
        for p in papers:
            it = by_doi.get(p['doi'] or '') or by_t.get(tkey(p['r'].get('title')) or '')
            q = p['doi'] or p['r'].get('title')
            out[p['key']] = check('repository', q, 'found' if it else 'none',
                                  dict(repository='KiltHub', usable=[it.get('url')], item=it.get('id')) if it else dict(repository='KiltHub', items_indexed=len(lst['items']), harvested=lst.get('fetched_at')))
        return out
    if school == 'epfl':
        S = F.P.archive_sweep('claude-epfl-20261019')
        sys.path.insert(0, str(F.P.vendor('epfl_tools')))  # vendored code (tools/vendor_sync.py); its data stays in S
        import epfl_infoscience_rest as eir
        rest = eir.load_cache()
        by_doi, by_t, k = {}, {}, 0
        for f in sorted((S / 'raw' / 'infoscience').glob('oai_marcxml_*.jsonl.gz')):
            for line in gzip.open(f, 'rt'):
                try:
                    x = json.loads(line)
                except ValueError:
                    continue
                k += 1
                rec = (x.get('h'), 'fulltext-public' in (x.get('sets') or []))
                if x.get('doi'):
                    by_doi.setdefault(F.ndoi(x['doi']), rec)
                if tkey(x.get('title')):
                    by_t.setdefault(tkey(x['title']), rec)
        for p in papers:
            hs = {m.group(1) for u in p['all_urls'] if (m := eir.HANDLE.match(u))}
            hit = by_doi.get(p['doi'] or '') or by_t.get(tkey(p['r'].get('title')) or '')
            if hit and hit[0]:
                hs.add('20.500.14299/' + hit[0])
            q = p['doi'] or p['r'].get('title')
            if not hs:
                out[p['key']] = check('repository', q, 'none', dict(repository='Infoscience', records_indexed=k, note='no Infoscience record with this DOI or title')); continue
            files = [x for h in hs for x in (rest.get(h) or {}).get('files') or [] if (x.get('name') or '').lower().endswith('.pdf')]
            resolved = all(h in rest and not rest[h].get('error') for h in hs)
            if files:
                out[p['key']] = check('repository', q, 'found', dict(repository='Infoscience', handles=sorted(hs), usable=[f"https://infoscience.epfl.ch/bitstreams/{x['uuid']}/download" for x in files][:3]))
            elif resolved:
                out[p['key']] = check('repository', q, 'none', dict(repository='Infoscience', handles=sorted(hs), note='Infoscience record without a public PDF'),
                                      at=max(rest[h]['at'] for h in hs))
            elif hit and hit[1]:
                out[p['key']] = check('repository', q, 'found', dict(repository='Infoscience', handles=sorted(hs), note='OAI set fulltext-public; files not resolved yet'))
            else:
                out[p['key']] = check('repository', q, 'none', dict(repository='Infoscience', handles=sorted(hs), note='record not in the fulltext-public set; REST files not resolved'))
        return out
    # berkeley, stanford: the repository refuses this client (eScholarship: HTTP 403 on robots.txt and every page,
    # 2026-10-30) or has no harvest interface used here (SDR); their holdings reach us through OpenAlex and CORE
    # michigan: Deep Blue is never used in any form (owner rule 2026-10-30), so only what OpenAlex and CORE list for it counts
    pat = re.compile({'berkeley': r'escholarship\.org|escholarship', 'michigan': r'deepblue\.lib\.umich\.edu|deep ?blue'}.get(
        school, r'purl\.stanford\.edu|stacks\.stanford\.edu|searchworks\.stanford\.edu|Stanford Digital Repository'), re.I)
    for p in papers:
        o, c = oa.get(p['key']) or {}, core.get(p['key']) or {}
        if o.get('result') not in ('found', 'none', 'not_applicable'):
            out[p['key']] = check('repository', p['key'], 'error', 'OpenAlex check missing'); continue
        od = o.get('detail') if isinstance(o.get('detail'), dict) else {}
        cd = c.get('detail') if isinstance(c.get('detail'), dict) else {}  # an unanswered CORE check carries a note, not links
        locs = [l for l in od.get('locations') or [] if pat.search(' '.join(str(l.get(x) or '') for x in ('host', 'source', 'landing', 'pdf')))]
        links = [u for u in cd.get('links') or [] if pat.search(u)]
        usable = [] if school == 'michigan' else [l['pdf'] for l in locs if l.get('pdf')] + links  # Deep Blue copies are never fetched
        out[p['key']] = check('repository', p['key'], 'found' if usable else 'none',
                              dict(repository=REPO[school], records=[l.get('landing') for l in locs][:3], usable=usable[:3],
                                   note=('Deep Blue is never asked (owner rule); ' if school == 'michigan' else 'direct access refused (HTTP 403) or not harvested; ') + 'checked through OpenAlex and CORE'), at=o.get('at'))
    return out


def src_labpages(school, papers, n):
    import labpage_channel as lc
    ev_ok = (F.P.data('labpage-evidence.json', school)).exists() or (F.P.data('labpage-pubs-report.json', school)).exists()
    cap = F.P.data('labpage-captures.sqlite', school)
    out = {}
    if not ev_ok or not cap.exists():
        for p in papers:
            out[p['key']] = check('labpages', ', '.join(p['r'].get('pis') or []), 'error', 'no lab-page captures for this school')
        return out
    urls, roots = lc.pi_pages(school)
    extra = RAW / f'pi-homepages-{school}.json'
    if extra.exists():
        for pi, us in json.loads(extra.read_text()).items():
            for u in us:
                urls[pi].add(lc.nurl(u)); roots[pi].add(lc.root_of(u))
    by_pi = defaultdict(list)
    for p in papers:
        for pi in p['r'].get('pis') or []:
            by_pi[pi].append((p['r'], p['key']))
    pages, per_pi = [], Counter()
    for url, final, capu, ct, content in lc.iter_captures(school):
        owners = lc.page_owners(url, final, urls, roots) & set(by_pi)
        if owners:
            base = lc.unwrap(final or url)
            pages.append((base if base.startswith('http') else lc.unwrap(url), owners, lc.decode(content), (ct or '').lower()))
            for o in owners:
                per_pi[o] += 1
    ph = RAW / 'pihomes.sqlite'
    if ph.exists():
        db = sqlite3.connect(f'file:{ph}?mode=ro', uri=True, timeout=60)
        for url, ok, body in db.execute('SELECT url, ok, body FROM pages'):
            if not ok:
                continue
            owners = lc.page_owners(url, url, urls, roots) & set(by_pi)
            if owners:
                import zlib
                pages.append((url, owners, zlib.decompress(body).decode('utf-8', 'replace'), 'text/html'))
                for o in owners:
                    per_pi[o] += 1
        db.close()
    rows, arx = lc.match_pages(pages, by_pi, defaultdict(set), Counter(), 'labpages', lambda k: False)
    found = defaultdict(list)
    for x in rows:
        found[x['work_id']].append(x['url'])
    for k, (a, pg) in arx.items():
        found[k].append('arXiv:' + a)
    for p in papers:
        pis = p['r'].get('pis') or []
        npg = sum(per_pi[pi] for pi in pis)
        q = ', '.join(pis)
        if found.get(p['key']):
            out[p['key']] = check('labpages', q, 'found', dict(usable=found[p['key']][:4], pages=npg))
        else:
            out[p['key']] = check('labpages', q, 'none', dict(pages=npg, note=None if npg else 'no lab or home page captured for the PI(s)'))
    return out


def src_wayback(papers, offline, n):
    log_f = RAW / 'wayback_lookups.jsonl'
    done = {}
    R = str(F.P.SWEEPS) + '/'
    for lf in (Path(R + 'claude-mit-20261020/raw/wayback_lookups.jsonl'), Path(R + 'claude-cmu-20261017/raw/wayback_lookups.jsonl'),
               Path(R + 'claude-epfl-20261019/raw/wayback_lookups.jsonl'), Path(R + 'claude-princeton-20261015/cs-structure/raw/wayback/lookups.jsonl'), log_f):
        if lf.exists():
            for line in lf.open():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r.get('status'), int) and r['status'] == 200:
                    done[re.sub(r'^https?://', '', r.get('url') or '')] = (r.get('capture'), r.get('at'))
    acm = {p['key']: f"dl.acm.org/doi/pdf/{p['doi']}" for p in papers if (p['doi'] or '').startswith('10.1145/')}
    todo = [u for u in dict.fromkeys(acm.values()) if u not in done]
    n['wayback_to_ask'] = len(todo)
    if todo and not offline:
        import requests
        s = requests.Session(); s.headers['User-Agent'] = UA
        last = 0.0
        with log_f.open('a') as f:
            for k, url in enumerate(todo):
                for attempt in range(6):
                    time.sleep(max(0, 8 - (time.monotonic() - last))); last = time.monotonic()
                    try:
                        r = s.get('https://web.archive.org/cdx/search/cdx', params=dict(url=url, output='json', fl='timestamp,original,mimetype,statuscode',
                                                                                       filter=['statuscode:200', 'mimetype:application/pdf'], limit=20), timeout=(15, 90))
                        status = r.status_code
                        caps = r.json()[1:] if status == 200 and r.text.strip() else []
                    except Exception as e:
                        status, caps = type(e).__name__, []
                    if not isinstance(status, int):
                        time.sleep(300); continue
                    if status == 429 or status >= 500:
                        time.sleep(120); continue
                    break
                else:
                    continue
                caps = [x for x in caps if 'casa_token' not in x[1] and 'cookieSet' not in x[1]]
                best = max(caps, key=lambda x: x[0]) if caps else None
                cap = dict(timestamp=best[0], original=best[1]) if best else None
                at = now()
                if status == 200:
                    done[url] = (cap, at)
                f.write(json.dumps(dict(work_id=None, kind='acm', url=url, status=status, capture=cap, at=at)) + '\n'); f.flush()
                if k % 200 == 199:
                    print(json.dumps(dict(wayback_asked=k + 1, of=len(todo))), flush=True)
    out = {}
    for p in papers:
        u = acm.get(p['key'])
        if not u:
            out[p['key']] = check('wayback_acm', None, 'not_applicable', 'not an ACM DOI'); continue
        if u not in done:
            out[p['key']] = check('wayback_acm', u, 'error', 'CDX lookup not done'); continue
        cap, at = done[u]
        out[p['key']] = check('wayback_acm', u, 'found' if cap else 'none',
                              dict(usable=[f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}"]) if cap else 'no PDF capture of the ACM DL PDF URL', at=at)
    return out


class ArxivIndex:
    """arxiv_oai.match_one over the local OAI index, plus the nearest title (word postings of the rarest title words)."""
    def __init__(self):
        import arxiv_oai as ao
        self.ao = ao
        self.idx = ao.index()
        self.recs, self.post = [], defaultdict(list)
        for f in sorted(ao.RAW.glob('*.jsonl.gz')):
            for line in gzip.decompress(f.read_bytes()).decode().splitlines():
                if not line:
                    continue
                r = json.loads(line)
                ws = set(ao.words(r['title']))
                if len(ws) < 2:
                    continue
                i = len(self.recs)
                self.recs.append((r['id'], r['title']))
                for w in ws:
                    self.post[w].append(i)
        self.built = max(datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) for f in ao.RAW.glob('*.jsonl.gz')).date().isoformat()

    def nearest(self, title):
        ws = sorted(set(self.ao.words(title)), key=lambda w: len(self.post.get(w, ())))
        ws = [w for w in ws if self.post.get(w)][:3]
        cand = Counter()
        for w in ws:
            ps = self.post[w]
            if len(ps) > 4000:
                continue
            for i in ps:
                cand[i] += 1
        if not cand:
            return None, 0.0
        a = self.ao.nt(title)
        best = (None, 0.0)
        for i, _ in cand.most_common(40):
            r = difflib.SequenceMatcher(None, a, self.ao.nt(self.recs[i][1])).ratio()
            if r > best[1]:
                best = (self.recs[i], r)
        return best


def src_arxiv(papers, oa, s2, dblp, n, idx_box):
    out = {}
    for p in papers:
        a, via = arxiv_known(p), 'paper identifiers'
        if not a:
            od = (oa.get(p['key']) or {}).get('detail')
            if isinstance(od, dict) and od.get('arxiv'):
                a, via = od['arxiv'], 'OpenAlex location'
        if not a:
            sd = (s2.get(p['key']) or {}).get('detail')
            if isinstance(sd, dict) and (sd.get('externalIds') or {}).get('ArXiv'):
                a, via = sd['externalIds']['ArXiv'], 'Semantic Scholar externalIds'
        if not a:
            dd = (dblp.get(p['key']) or {}).get('detail')
            for u in (dd.get('usable') or []) if isinstance(dd, dict) else []:
                if u.startswith('arXiv:'):
                    a, via = u[6:], 'DBLP CoRR record'
        q = p['r'].get('title')
        if a:
            out[p['key']] = check('arxiv', q, 'found', dict(arxiv=a, via=via, usable=['arXiv:' + a])); continue
        if len(F.nt(q)) < 20:
            out[p['key']] = check('arxiv', q, 'none', dict(note='no arXiv id; title too short to match')); continue
        if idx_box.get('idx') is None:
            print(json.dumps(dict(loading='arXiv OAI index')), flush=True)
            idx_box['idx'] = ArxivIndex()
        ix = idx_box['idx']
        people = list(p['r'].get('byline') or []) + list(p['r'].get('pis') or [])
        aid, tier = ix.ao.match_one(ix.idx, q, p['r'].get('year'), people)
        if aid:
            out[p['key']] = check('arxiv', q, 'found', dict(arxiv=aid, via='arXiv OAI index ' + tier, usable=['arXiv:' + aid], index_built=ix.built)); continue
        rec, sim = ix.nearest(q)
        out[p['key']] = check('arxiv', q, 'none', dict(note='no arXiv id; no title match in the arXiv index (2015-)', index_built=ix.built,
                                                        best_candidate=dict(arxiv=rec[0], title=rec[1]) if rec else None, similarity=round(sim, 3)))
    return out


def crossref_names(prefixes, offline):
    f = RAW / 'crossref_prefixes.json'
    cache = json.loads(f.read_text()) if f.exists() else {}
    todo = [p for p in prefixes if p not in cache and p not in PREFIX_PUB]
    if todo and not offline:
        import requests
        s = requests.Session(); s.headers['User-Agent'] = UA
        for p in todo:
            time.sleep(1.0)
            try:
                r = s.get(f'https://api.crossref.org/prefixes/{p}', timeout=(15, 60))
                cache[p] = (r.json().get('message') or {}).get('name') if r.status_code == 200 else None
            except Exception:
                continue
        f.write_text(json.dumps(cache, indent=0))
    return cache


# ---------------------------------------------------------------- the decision

def norm_found(u):
    m = re.search(r'arxiv-dataset/arxiv/arxiv/pdf/\d+/(\d{4}\.\d{4,5})|arxiv\.org/(?:abs|pdf)/([^\s?#v]+(?:\.\d+)?)', u)
    if m:
        return 'arXiv:' + (m.group(1) or m.group(2))
    m = re.search(r'PMC(\d+)\.\d+/PMC|pmc/articles/PMC(\d+)|PMC(\d+)$', u)
    if m and ('pmc' in u.lower()):
        return 'PMC' + next(g for g in m.groups() if g)
    return re.sub(r'^https?://', '', u).rstrip('/')


def decide(p):
    """(reason_code, missing_checks, new_open_urls) for one assembled paper (a pure function of the record: tests feed it
    fixtures). p: status, doi, attempts [{url, cause}], untried [url], access {verdict, cause}, checks {source: check},
    applicable [source], in_catalog."""
    chk = p['checks']
    missing = [s for s in p['applicable'] if (chk.get(s) or {}).get('result') not in ('found', 'none', 'not_applicable')]
    known = {norm_found(u) for u in p.get('all_urls') or []} | {norm_found(a['url']) for a in p['attempts']}
    found = []
    for s, c in chk.items():
        if c and c.get('result') == 'found':
            d = c.get('detail') if isinstance(c.get('detail'), dict) else {}
            for u in d.get('usable') or d.get('urls') or d.get('files') or []:
                found.append(u)
    new = [u for u in dict.fromkeys(found) if norm_found(u) not in known]
    if p['untried']:
        return 'found_awaiting_download', missing, new
    if new:
        return ('found_awaiting_download' if p['in_catalog'] else 'found_not_in_catalog'), missing, new
    if p.get('quarantined'):  # a copy was taken from a path robots.txt disallows for an Anthropic crawler; quarantined
        return 'open_copy_robots_disallowed', missing, new
    if p.get('status') == 'identity_unconfirmed':  # a copy is downloaded, but its identity is not confirmed (identity_rule.py)
        return 'identity_unconfirmed', missing, new
    per_url = defaultdict(list)
    for a in p['attempts']:
        per_url[a['url']].append(a['cause'])
    acc = p.get('access') or {}
    transient = {'transient', 'transient_exhausted', 'transient_on_challenge_or_publisher_host'}
    pending = [u for u, cs in per_url.items() if set(cs) <= transient | {'other'} and 'transient' in cs] + \
              [u for u, cs in per_url.items() if 'unapproved_redirect' in cs and not set(cs) - {'unapproved_redirect', 'transient'}]
    if (acc.get('verdict') or '').startswith('requeue') or (pending and len(pending) == len(per_url)) or (p['status'] == 'queued' and pending):
        return 'pending_retry', missing, new
    if missing:
        return 'incomplete_check', missing, new
    from review_access import PUBLISHERS
    opn = {u: cs for u, cs in per_url.items() if not PUBLISHERS.search(host(u)) and host(u) not in ('doi.org', 'dx.doi.org')}
    allc = {c for cs in opn.values() for c in cs}
    if opn:
        for c, code in (('challenge', 'open_copy_bot_challenge'), ('login', 'open_copy_behind_login'), ('robots_disallow', 'open_copy_robots_disallowed'),
                        ('robots_unavailable', 'open_copy_robots_disallowed')):
            if c in allc:
                return code, missing, new
        if allc & {'landing_no_pdf', 'publisher_landing_no_pdf', 'policy_skip'}:
            return 'landing_page_without_pdf', missing, new
        if allc & {'not_found', 'identity_mismatch', 'not_pdf', 'too_large', 'tls_error', 'integrity_mismatch', 'embargoed', 'other', 'transient_exhausted',
                   'unapproved_redirect', 'transient_on_challenge_or_publisher_host'}:
            return 'open_copy_unusable', missing, new
        if 'paywall_or_forbidden' in allc:
            return 'paywall_only', missing, new
    oad = (chk.get('openalex') or {}).get('detail') if isinstance((chk.get('openalex') or {}).get('detail'), dict) else {}
    if not p['doi']:
        return 'no_doi_no_match', missing, new
    if oad.get('is_oa') and per_url:
        # open at the publisher (gold / hybrid / bronze), and the publisher's own host refused this client: say how
        pubc = {c for cs in per_url.values() for c in cs}
        for c, code in (('challenge', 'open_copy_bot_challenge'), ('login', 'open_copy_behind_login'), ('robots_disallow', 'open_copy_robots_disallowed')):
            if c in pubc:
                return code, missing, new
        return 'paywall_only', missing, new
    if oad.get('is_oa'):
        return 'landing_page_without_pdf', missing, new
    return 'publisher_only_closed', missing, new


def summarize(p, code, missing, new):
    chk = p['checks']
    oad = (chk.get('openalex') or {}).get('detail') if isinstance((chk.get('openalex') or {}).get('detail'), dict) else {}
    pub, venue = p.get('publisher') or 'an unknown publisher', p.get('venue')
    access = 'closed access' if oad.get('is_oa') is False else (f"OpenAlex: {oad.get('oa_status')}" if oad.get('oa_status') else 'access status unknown')
    s = [f"At {pub} ({access}{', ' + venue if venue else ''})." if p['doi'] else f"No DOI ({access})."]
    ac = chk.get('arxiv') or {}
    ad = ac.get('detail') if isinstance(ac.get('detail'), dict) else {}
    if ac.get('result') == 'found':
        s.append(f"arXiv version {ad.get('arxiv')} ({ad.get('via')}).")
    elif ac:
        bc = ad.get('best_candidate')
        s.append('No arXiv version (no arXiv id; ' + (f"best title match {ad.get('similarity')})." if bc else 'no title match).'))
    checked = [LABEL[x] if x != 'repository' else REPO.get(p['school'], 'the school repository') for x in p['applicable']
               if x != 'arxiv' and (chk.get(x) or {}).get('result') == 'none']
    if checked:
        s.append('No open copy in ' + (', '.join(checked[:-1]) + ' or ' + checked[-1] if len(checked) > 1 else checked[0]) +
                 f"; checked {(p['checked_at'] or '')[:10]}.")
    fnd = [LABEL[x] for x in p['applicable'] if (chk.get(x) or {}).get('result') == 'found']
    if fnd:  # every location these sources list was tried (else the code is found_awaiting_download)
        s.append(('Locations listed by ' if code not in ('found_awaiting_download', 'found_not_in_catalog') else 'Open copy listed by ') + ', '.join(fnd) +
                 (' were tried (attempts below).' if code not in ('found_awaiting_download', 'found_not_in_catalog') else '.'))
    if missing:
        s.append('Not checked yet: ' + ', '.join(LABEL[x] for x in missing) + '.')
    if p['attempts']:
        last = {}
        for a in p['attempts']:
            last[a['url']] = a
        ex = '; '.join(f"{host(a['url'])} {a['cause']}" for a in list(last.values())[-3:])
        s.append(f"{len(p['attempts'])} download attempt{'s' if len(p['attempts']) != 1 else ''} ({len(last)} URL{'s' if len(last) != 1 else ''}): {ex}.")
    elif p['in_catalog']:
        s.append('No download attempt (no candidate URL).')
    else:
        s.append('Not in the full-text catalog.')
    lead = {'found_awaiting_download': f"Open copy waiting for the collector ({(p['untried'] or new or ['?'])[0][:120]}).",
            'found_not_in_catalog': 'Open copy found, but the paper has no catalog work yet.',
            'pending_retry': 'Temporary failure; the collector asks again.',
            'identity_unconfirmed': 'A copy is downloaded, but neither its title nor its authors confirm it is this paper; it does not count until confirmed.',
            'incomplete_check': 'Checks incomplete.'}.get(code)
    return ' '.join(([lead] if lead else []) + s)


def applicable(p, school):
    a = ['openalex', 'arxiv', 's2', 'dblp', 'proceedings', 'repository', 'labpages']
    if p['doi'] and not p['doi'].startswith('10.48550/'):
        a.append('core')
    if (p['doi'] or '').startswith('10.1145/'):
        a.append('wayback_acm')
    return a


# ---------------------------------------------------------------- main

def run(schools, max_age, offline, only=None, skip=()):
    global MAX_AGE
    MAX_AGE = max_age
    F.load_env()
    n = Counter()
    by_school = {}
    for s in schools:
        t0 = time.time()
        if not (F.P.data('copies.json', s)).exists():  # an onboarding school before its first copies stage
            sys.path.insert(0, str(F.SCHOOLS / 'tools'))
            import lab_paper_copies
            lab_paper_copies.run(s)
        ps = load_school(s)
        if only:
            ps = {k: v for k, v in ps.items() if k == only}
        by_school[s] = list(ps.values())
        print(json.dumps(dict(school=s, non_local=len(ps), load_s=round(time.time() - t0))), flush=True)
    allp = [p for ps in by_school.values() for p in ps]
    # reuse fresh ledger checks from the store (same query, younger than the source's max age)
    prior = {s: C.latest(s, channels={'ledger.' + x for x in SOURCES}) for s in schools}

    def reuse(s, p, src, age):
        c = prior[s].get((p['key'], 'ledger.' + src))
        if c and c['result'] in ('found', 'none', 'not_applicable') and C.age_days(c['at']) <= age:
            return dict(source=src, at=c['at'], query=c['query'], result=c['result'], detail=c['detail'])
        return None

    res = {x: {} for x in SOURCES}
    fresh_new = {x: set() for x in SOURCES}

    def stage(src, age, fn, papers_by_school):
        need = {}
        for s, ps in papers_by_school.items():
            for p in ps:
                c = reuse(s, p, src, age)
                if c:
                    res[src][(s, p['key'])] = c
                else:
                    need.setdefault(s, []).append(p)
        t0 = time.time()
        if need:
            got = fn(need)
            for s, d in got.items():
                for k, c in d.items():
                    res[src][(s, k)] = c; fresh_new[src].add((s, k))
        print(json.dumps(dict(source=src, reused=sum(len(ps) for ps in papers_by_school.values()) - sum(len(v) for v in need.values()), asked=sum(len(v) for v in need.values()),
                              seconds=round(time.time() - t0))), flush=True)

    per = lambda src: {s: {k: c for (s2_, k), c in res[src].items() if s2_ == s} for s in schools}
    stage('openalex', OA_AGE, lambda need: {s: src_openalex(ps, offline, n) for s, ps in need.items()}, by_school)
    oa = {k: c for (s, k), c in res['openalex'].items()}
    oa_s = per('openalex')
    stage('s2', MAX_AGE, lambda need: {s: src_s2(ps, oa_s[s], offline or 's2' in skip, n, 0 if 's2_title' in skip else None) for s, ps in need.items()}, by_school)
    stage('core', MAX_AGE, lambda need: {s: src_core(ps, offline or 'core' in skip, n) for s, ps in need.items()}, by_school)
    s2_s, core_s = per('s2'), per('core')
    stage('pmc', MAX_AGE, lambda need: {s: src_pmc(ps, oa_s[s], s2_s[s], offline, n) for s, ps in need.items()}, by_school)
    stage('dblp', MAX_AGE, lambda need: src_dblp(need, offline or 'dblp' in skip, n), by_school)
    dblp_s = per('dblp')
    stage('proceedings', MAX_AGE, lambda need: {s: src_proceedings(ps, n) for s, ps in need.items()}, by_school)
    stage('repository', MAX_AGE, lambda need: {s: src_repository(s, ps, oa_s[s], core_s[s], offline, n) for s, ps in need.items()}, by_school)
    stage('labpages', MAX_AGE, lambda need: {s: src_labpages(s, ps, n) for s, ps in need.items()}, by_school)
    stage('wayback_acm', MAX_AGE, lambda need: {s: src_wayback(ps, offline or 'wayback_acm' in skip, n) for s, ps in need.items()}, by_school)
    box = {}
    stage('arxiv', MAX_AGE, lambda need: {s: src_arxiv(ps, oa_s[s], s2_s[s], dblp_s[s], n, box) for s, ps in need.items()}, by_school)
    prefixes = sorted({p['doi'].split('/', 1)[0] for p in allp if p['doi']})
    xref = crossref_names(prefixes, offline)
    at = now()
    for s in schools:
        recs = []
        for p in by_school[s]:
            p['checks'] = {x: res[x].get((s, p['key'])) for x in SOURCES if res[x].get((s, p['key']))}
            p['applicable'] = applicable(p, s)
            pmc = p['checks'].get('pmc')
            if pmc and pmc['result'] != 'not_applicable':
                p['applicable'].append('pmc')
            p['in_catalog'] = bool(p['group'])
            p['checked_at'] = at
            oad = (p['checks'].get('openalex') or {}).get('detail')
            oad = oad if isinstance(oad, dict) else {}
            pre = (p['doi'] or '').split('/', 1)[0]
            p['publisher'] = fold_publisher(oad.get('publisher')) or PREFIX_PUB.get(pre) or fold_publisher(xref.get(pre)) or ('arXiv' if pre == '10.48550' else None)
            p['venue'] = oad.get('venue')
            code, missing, new = decide(p)
            rec = dict(key=p['key'], school=s, work_id=p['cid'], status=p['status'], reason_code=code, final=REASONS[code],
                       summary=summarize(p, code, missing, new), publisher=p['publisher'] or 'unknown', venue=p['venue'], doi=p['doi'],
                       year=p['r'].get('year'), title=p['r'].get('title'), is_oa=oad.get('is_oa'), oa_status=oad.get('oa_status'),
                       arxiv=((p['checks'].get('arxiv') or {}).get('detail') or {}).get('arxiv') if isinstance((p['checks'].get('arxiv') or {}).get('detail'), dict) else None,
                       checked_at=at, checks=[p['checks'][x] for x in SOURCES if x in p['checks']], missing_checks=missing,
                       attempts=[dict(url=a['url'], at=a['at'], status=a['status'], cause=a['cause'], detail=a['detail'][:200]) for a in p['attempts']],
                       access_review=p['access'], untried_candidates=p['untried'][:10], new_open_urls=new[:10])
            recs.append(rec)
        if not only:
            out = F.P.SchoolDir(s)
            F.P.data_w('unavailable.jsonl.gz', s)   # the directory first
            jdump(out / 'unavailable.jsonl.gz', recs)
            by_r = Counter(r['reason_code'] for r in recs)
            by_p = Counter(r['publisher'] for r in recs)
            by_rp = defaultdict(Counter)
            for r in recs:
                by_rp[r['reason_code']][r['publisher']] += 1
            lp = F.P.data('lab_papers.jsonl.gz', s)
            summ = dict(school=s, built_at=at, max_age_days=MAX_AGE, offline=offline,
                        inputs=dict(copies_json=datetime.fromtimestamp((out / 'copies.json').stat().st_mtime, timezone.utc).isoformat(),
                                    lab_papers=datetime.fromtimestamp(lp.stat().st_mtime, timezone.utc).isoformat()),
                        papers=len(recs), by_reason=dict(by_r.most_common()), by_publisher=dict(by_p.most_common(40)),
                        by_reason_publisher={k: dict(v.most_common(15)) for k, v in by_rp.items()},
                        final=sum(1 for r in recs if r['final']), not_final=sum(1 for r in recs if not r['final']),
                        missing_checks=dict(Counter(m for r in recs for m in r['missing_checks']).most_common()))
            tmp = (out / 'unavailable-summary.json').with_name(f'.unavailable-summary.json.{os.getpid()}.part')
            tmp.write_text(json.dumps(summ, indent=1)); os.replace(tmp, out / 'unavailable-summary.json')
            # the new checks into the store (reused ones are already there)
            rows = []
            for p in by_school[s]:
                for x in SOURCES:
                    if (s, p['key']) in fresh_new[x] and p['checks'].get(x):
                        c = p['checks'][x]
                        rows.append(dict(paper_key=p['key'], work_id=p['cid'], channel='ledger.' + x, at=c.get('at') or at,
                                         query=c.get('query'), result=c['result'], detail=c.get('detail')))
            n[f'{s}_checks_recorded'] = C.record(s, rows)
            sys.path.insert(0, str(F.SCHOOLS / 'tools'))
            import lab_paper_copies
            lab_paper_copies.attach_ledger(s)
            print(json.dumps(dict(school=s, papers=len(recs), by_reason=summ['by_reason'], missing=summ['missing_checks'])), flush=True)
        else:
            for r in recs:
                print(json.dumps(r, indent=1, default=str))
    print(json.dumps(dict(done=at, **n)), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--max-age-days', type=float, default=MAX_AGE)
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--no-network-sources', default='', help='comma list of s2, s2_title, core, dblp, wayback_acm not asked this run')
    a = ap.parse_args()
    run(a.schools, a.max_age_days, a.offline, a.only, set(filter(None, a.no_network_sources.split(','))))


if __name__ == '__main__':
    main()
