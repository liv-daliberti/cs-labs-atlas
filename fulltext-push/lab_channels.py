"""Open-copy channels for the CS lab papers that still have no local copy (2026-10-22 push), one school at a time.

missing   lab papers (hierarchy/<school>/lab_papers.jsonl.gz) without a copy by the coverage counter's rule (any catalog
          work with the same id, DOI or normalized title has one), matched to their catalog work (collection id, the
          push's <school>_oa_<W id>, DOI, title). Catalogs are read in short rowid chunks; every candidate write commits
          per batch (the collectors wait at most 120 s for a lock). Known URLs = the work's candidates and attempts.
steps (each adds candidates only for works with no copy, and only URLs not already known for the work):
  oa_arxiv    the paper's arXiv id (10.48550 DOI, or an arXiv location in its OpenAlex record) -> arXiv's bulk copy on
              GCS (storage.googleapis.com/arxiv-dataset; ../../claude-cmu-20261017/tools/arxiv_bulk.py listing), never arxiv.org
  openalex    the paper's OpenAlex record (hierarchy/<school>/pi-works.sqlite): open pdf_urls, repository pdf_urls and
              landing pages on hosts the collectors may use; PubMed Central locations -> NLM's PMC open-data copy on S3
  arxiv_title papers with no arXiv link: a match in the local arXiv OAI-PMH index (../../claude-cmu-20261017/tools/
              arxiv_oai.py match_one: exact normalized title / same significant words / with-or-without subtitle, a
              shared author family name with the paper's byline, first version 1 year after to 3 years before) -> bulk copy
  proceedings the open proceedings index of the Princeton sweep (NeurIPS, PMLR, ICLR, CVF, ACL, IJCAI, USENIX, JMLR, ...):
              same normalized title, year within 2 -> the PDF on the proceedings host
  s2          Semantic Scholar /paper/batch by DOI or arXiv id with the user's key (S2_API_KEY from ~/.config/cs-atlas/s2.env
              only; one request per 1.2 s shared across processes): ArXiv id -> bulk copy, PMCID -> PMC S3,
              ACL id -> aclanthology.org, openAccessPdf on a usable host (../../claude-cmu-20261017/tools/s2_key_lookup.py)
  core        CORE search API, 25 DOIs per request (CORE_API_KEY; repository links only; core_search.usable)
  europepmc   Europe PMC search by DOI (10 s per query) -> PMCID -> the PMC open-data files on S3
  pmc         PMC article links among known URLs -> the PMC open-data files on S3 (robots.txt disallows /pmc/articles)
  figshare    Figshare / KiltHub articles named by a DOI or link -> api.figshare.com file list -> ndownloader links
  techrpt     (berkeley) EECS Technical Reports: the year indexes www2.eecs.berkeley.edu/Pubs/TechRpts/<year>/
              (robots.txt disallows only /Protected; one request per 3 s), a report whose normalized title equals the
              paper's -> its report page -> the report PDF
  pubpages    (berkeley) the EECS Faculty Publications pages already captured (hierarchy/berkeley/pubs-pages.sqlite): an
              entry whose linked title equals the paper's and whose link is a PDF / arXiv / open host
  homepages   (berkeley) author- and lab-hosted PDFs: the PI's website and their units' websites, plus pages they link
              as publications; the one PDF / arXiv link of the bibliography entry carrying the paper's exact title
  dspace      (mit) DSpace@MIT handles among the works' links -> OAI-PMH ORE file lists -> REST bitstreams (8 s per request)
  infoscience (epfl) Infoscience handles among the works' links -> the REST API's ORIGINAL PDFs (epfl_infoscience_rest.py)
  labpages    (every school) the free PDFs / arXiv links that the PI's own lab publication pages carry for the paper, from the
              lab-pages passes' captures (hierarchy/<school>/labpage-captures.sqlite; labpage_channel.py)
  pihomes     (every school) fallback: the PI's homepage and the publication pages it links, fetched once when the
              captures lack them (robots.txt, 3 s per request; raw/pihomes.sqlite), same matcher (labpage_channel.py)
  oar         (princeton) Princeton's Open Access Repository items already crawled by the Princeton stage, by DOI or title
              (repo_index.py)
  wayback_acm DOIs 10.1145/* of works without an arXiv candidate: exact-URL Wayback CDX lookups of dl.acm.org/doi/pdf/<doi> (one per 8 s; 200 + application/pdf
              captures only, no casa_token subscriber links) -> web.archive.org/web/<ts>id_/<url> (the collector asks
              web.archive.org at most once per 6 s). ACM DL is open access since January 2026 but refuses automated clients.
The collector's identity check (the catalog title in the file, or the arXiv id against an arXiv DOI) applies to every
candidate, and its title-mismatch rejections stand.
Candidates go straight into data/fulltext/<school>/catalog.sqlite (CMU, EPFL, MIT, Berkeley; evidence under
discovery/claude-<school>-labpapers/evidence/), for Princeton into a discovery package
data/fulltext/princeton/discovery/claude-labpapers-<step>-<stamp>/ (cs_open_copies format) for its import path.
Counts -> fulltext-push/logs/channels.jsonl.
usage: lab_channels.py <school> <step> [<step> ...] [--dry]   (runs channel_runner.py: each step is the plugin channels/<step>.py)
"""
import html, json, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

HERE = F.HERE
UA = F.UA


def plan_for(school):
    papers = F.lab_papers(school)
    cs = F.catalog_state(school)
    miss, n = [], Counter()
    for k, r in papers.items():
        if F.is_local(school, r, cs):
            n['local'] += 1; continue
        w = F.match_work(school, r, cs)
        if not w:
            n['not_in_catalog'] += 1; continue
        n['missing_in_catalog'] += 1
        miss.append((r, w))
    known = defaultdict(set)
    for r, w in miss:
        known[w] |= cs['urls'].get(w, set())
    if school == 'princeton':  # candidates waiting in discovery packages count as known
        for f in (F.FT / 'princeton' / 'discovery').glob('claude-*/*candidates.jsonl'):
            ws = {w for _, w in miss}
            for line in f.open():
                c = json.loads(line)
                if c['work_id'] in ws:
                    known[c['work_id']].add(c['url'])
    print(json.dumps(dict(school=school, **n)), flush=True)
    return miss, known, n


def has_arxiv(urls):
    from cs_open_copies import arxiv_id
    return any(arxiv_id(u) or 'arxiv-dataset/arxiv/arxiv/pdf/' in u for u in urls)


def new_rows(rows, known):
    out = []
    for r in rows:
        if r['url'] not in known[r['work_id']]:
            known[r['work_id']].add(r['url']); out.append(r)
    return out


# ---------------------------------------------------------------- steps

def step_oa_arxiv(school, miss, known, n):
    bodies = F.oa_bodies(school, [r['oa'] for r, _ in miss])
    want = {}
    for r, w in miss:
        if has_arxiv(known[w]):
            continue
        a = F.arxiv_of(r, bodies.get(r['oa']))
        if a:
            want[w] = a
    rows, n['oa_arxiv_not_in_bulk'] = F.bulk_rows(want, 'openalex_arxiv_bulk')
    return rows


def step_openalex(school, miss, known, n):
    import requests
    bodies = F.oa_bodies(school, [r['oa'] for r, _ in miss])
    lacking = [r['oa'] for r, _ in miss if r['oa'] not in bodies]
    if lacking:
        bodies.update(F.fetch_oa_bodies(lacking))
    rows, pmc = [], {}
    for r, w in miss:
        rs, p = F.oa_location_rows(w, bodies.get(r['oa']))
        rows += rs
        if p and not any('pmc-oa-opendata' in u for u in known[w]):
            pmc[w] = p
    s = requests.Session(); s.headers['User-Agent'] = UA
    memo = {}
    for w, p in pmc.items():
        rows += F.pmc_rows(w, p, memo, s)
    return rows


def step_arxiv_title(school, miss, known, n):
    import arxiv_oai
    idx = arxiv_oai.index()
    sess = re.compile(r'^\s*\d+(?:\.\d+)+\s+(?=\S)')
    want = {}
    for r, w in miss:
        if has_arxiv(known[w]):
            continue
        people = list(r.get('byline') or []) + list(r.get('pis') or [])
        aid, tier = arxiv_oai.match_one(idx, r['title'], r.get('year'), people)
        if not aid and sess.match(r['title'] or ''):
            aid, tier = arxiv_oai.match_one(idx, sess.sub('', r['title']), r.get('year'), people)
            tier = tier and tier + '_without_session_number'
        if aid:
            want[w] = aid; n['arxiv_title:' + tier] += 1
    rows, n['arxiv_title_not_in_bulk'] = F.bulk_rows(want, 'arxiv_oai_title_match')
    return rows


def step_s2(school, miss, known, n):
    import os
    os.environ['S2_BATCH_ONLY'] = '1'
    import s2_key_lookup as s2k
    cs = F.catalog_state(school, with_urls=False)
    targets = []
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        if not d:
            a = F.arxiv_of(r, None)
            d = f'10.48550/arxiv.{a}' if a else None
        if not d:
            continue
        targets.append(dict(school=school, work_id=w, doi=d, corpus=None, title=r['title'], year=r.get('year'), people=list(r.get('byline') or [])))
    cache = s2k.fetch(targets)
    found, cn = s2k.candidates(targets, defaultdict(set, {w: set(u) for w, u in known.items()}), cache)  # a copy: candidates() marks its own URLs known
    for k, v in cn.items():
        n['s2_' + k] += v
    return [dict(work_id=t['work_id'], url=u, landing_url=land, version=ver, source=src, detail=det) for t, u, land, ver, src, det in found]


def step_core(school, miss, known, n):
    import os, requests
    import core_search as cs
    s = requests.Session(); s.headers['Authorization'] = 'Bearer ' + os.environ['CORE_API_KEY']
    done = {}
    if cs.CACHE.exists():
        for line in cs.CACHE.open():
            try:
                r = json.loads(line); done[r['doi']] = r
            except ValueError:
                pass
    dois = [F.ndoi(r['doi']) for r, _ in miss if r.get('doi') and not F.ndoi(r['doi']).startswith('10.48550/')]
    todo = list(dict.fromkeys(d for d in dois if '"' not in d and '\\' not in d and (d not in done or done[d].get('error'))))
    print(json.dumps(dict(core_dois=len(set(dois)), todo=len(todo))), flush=True)
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
            at = F.now()
            for d in chunk:
                rec = dict(doi=d, at=at, links=list(dict.fromkeys(got.get(d, [])))) if res is not None else dict(doi=d, at=at, error=True)
                done[d] = rec; f.write(json.dumps(rec) + '\n')
            f.flush()
            if (i // 25) % 40 == 39:
                print(json.dumps(dict(core_asked=i + len(chunk), of=len(todo))), flush=True)
    rows = []
    for r, w in miss:
        if not r.get('doi'):
            continue
        for u in (done.get(F.ndoi(r['doi'])) or {}).get('links') or []:
            if cs.usable(u):
                rows.append(dict(work_id=w, url=u, landing_url=u, version=None, source='core_search', detail=F.ndoi(r['doi'])))
    return rows


def _study_plan(school, miss, known):
    return {school: ([(dict(work_key=w, doi=r.get('doi'), title=r['title'], year=r.get('year'), faculty=list(r.get('byline') or []), students=[]), w)
                      for r, w in miss], known)}


def step_pmc(school, miss, known, n):
    sys.path.insert(0, str(F.P.vendor('homogenization_tools')))
    import study_copies as sc
    rows = sc.pmc_rows(_study_plan(school, miss, defaultdict(set, {w: set(u) for w, u in known.items()})), n).get(school, [])  # a copy, as above
    return [dict(r, source='pmc_open_data') for r in rows]


def step_figshare(school, miss, known, n):
    sys.path.insert(0, str(F.P.vendor('homogenization_tools')))
    import study_copies as sc
    plan = _study_plan(school, miss, {w: set(u) for w, u in known.items()})
    return [dict(r, source='figshare_api') for r in sc.figshare_rows(plan, n).get(school, [])]


class Pacer:
    def __init__(self, delay):
        self.delay, self.last = delay, 0.0

    def wait(self):
        time.sleep(max(0, self.delay - (time.monotonic() - self.last))); self.last = time.monotonic()


def polite_get(s, url, pacer, robots):
    from urllib.parse import urlsplit
    h = urlsplit(url).hostname
    if h not in robots:
        from protego import Protego
        pacer.wait()
        try:
            r = s.get(f'https://{h}/robots.txt', timeout=(15, 30))
            robots[h] = Protego.parse(r.text if r.status_code == 200 else ('' if r.status_code == 404 else 'User-agent: *\nDisallow: /\n'))
        except Exception:
            robots[h] = Protego.parse('User-agent: *\nDisallow: /\n')
    if not robots[h].can_fetch(url, UA):
        return None
    pacer.wait()
    for attempt in range(3):
        try:
            r = s.get(url, timeout=(15, 60))
            if r.status_code == 200:
                return r.text
            if r.status_code in (429, 503):
                time.sleep(60); continue
            return None
        except Exception:
            time.sleep(15)
    return None


def step_techrpt(school, miss, known, n):
    assert school == 'berkeley'
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    pacer, robots = Pacer(3.0), {}
    cache_f = F.P.FT_RAW / 'eecs_techrpts.jsonl'
    cache = {}
    if cache_f.exists():
        for line in cache_f.open():
            r = json.loads(line); cache[r['key']] = r
    year_now = datetime.now(timezone.utc).year
    with cache_f.open('a') as f:
        for y in range(2015, year_now + 1):
            key = f'index:{y}'
            if key in cache and (y < year_now - 1):
                continue
            body = polite_get(s, f'https://www2.eecs.berkeley.edu/Pubs/TechRpts/{y}/', pacer, robots)
            if body is None:
                continue
            reps = [dict(html=m.group(1), title=html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip(), number=m.group(3), authors=html.unescape(m.group(4)).strip())
                    for m in re.finditer(r'<a href="(/Pubs/TechRpts/\d{4}/[^"]+\.html)">(.*?)</a>\s*\(([^)]+)\)\s*<br>\s*([^<]*)</p>', body, re.S)]
            rec = dict(key=key, at=F.now(), reports=reps)
            cache[key] = rec; f.write(json.dumps(rec) + '\n'); f.flush()
        by_title = defaultdict(list)
        for k, rec in cache.items():
            if k.startswith('index:'):
                for rep in rec['reports']:
                    if len(F.nt(rep['title'])) >= 20:
                        by_title[F.nt(rep['title'])].append(rep)
        n['techrpt_reports_indexed'] = sum(len(v) for v in by_title.values())
        rows = []
        for r, w in miss:
            for rep in by_title.get(F.nt(r['title']), []):
                page = 'https://www2.eecs.berkeley.edu' + rep['html']
                key = 'page:' + rep['html']
                if key not in cache:
                    body = polite_get(s, page, pacer, robots)
                    pdfs = re.findall(r'href="(https?://www2\.eecs\.berkeley\.edu/Pubs/TechRpts/[^"]+\.pdf)"', body or '')
                    cache[key] = dict(key=key, at=F.now(), pdfs=list(dict.fromkeys(pdfs)), ok=body is not None)
                    f.write(json.dumps(cache[key]) + '\n'); f.flush()
                for u in cache[key]['pdfs'][:1]:
                    u = re.sub(r'^http://', 'https://', u)
                    rows.append(dict(work_id=w, url=u, landing_url=page, version=None, source='eecs_techrpt_title_match', detail=rep['number']))
                    n['techrpt_title_matches'] += 1
    return rows


def step_pubpages(school, miss, known, n):
    assert school == 'berkeley'
    import zlib
    import s2_key_lookup as s2k, core_search as cs
    from cs_open_copies import arxiv_id
    db = sqlite3.connect(f"file:{F.P.data('pubs-pages.sqlite', 'berkeley')}?mode=ro", uri=True)
    by_title = defaultdict(list)
    for pi, url, body in db.execute('SELECT pi, url, body FROM pages WHERE status=200'):
        try:
            b = zlib.decompress(body).decode('utf-8', 'replace')
        except Exception:
            b = body.decode('utf-8', 'replace') if isinstance(body, bytes) else (body or '')
        for m in re.finditer(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S):
            t = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
            if len(F.nt(t)) >= 20:
                by_title[F.nt(t)].append((html.unescape(m.group(1)), url))
    rows, arx = [], {}
    for r, w in miss:
        for link, page in by_title.get(F.nt(r['title']), []):
            a = arxiv_id(link)
            if a:
                if not has_arxiv(known[w]):
                    arx[w] = re.sub(r'v\d+$', '', a)
                continue
            if re.search(r'\.pdf(?:$|[?#])', link, re.I) and s2k.ok_pdf(link) and cs.usable(link) and 'delivery.acm.org' not in link:
                rows.append(dict(work_id=w, url=link, landing_url=page, version=None, source='eecs_faculty_publications_page', detail=page))
                n['pubpages_pdf_links'] += 1
    brows, n['pubpages_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'eecs_faculty_publications_arxiv_bulk')
    return rows + brows


def step_wayback_acm(school, miss, known, n):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    log_f = F.P.FT_RAW / 'wayback_lookups.jsonl'
    done = {}
    R = str(F.P.SWEEPS) + '/'  # earlier lookups by the school stages are reused, not repeated
    for lf in (log_f, Path(R + 'claude-mit-20261020/raw/wayback_lookups.jsonl'), Path(R + 'claude-cmu-20261017/raw/wayback_lookups.jsonl'),
               Path(R + 'claude-epfl-20261019/raw/wayback_lookups.jsonl'), Path(R + 'claude-princeton-20261015/cs-structure/raw/wayback/lookups.jsonl')):
        if lf.exists():
            for line in lf.open():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r.get('status'), int) and r['status'] == 200:
                    done[re.sub(r'^https?://', '', r.get('url') or '')] = r.get('capture')
    targets = []
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        # works with an arXiv candidate are left for a later run: the bulk copy usually serves them
        if d.startswith('10.1145/') and not any('web.archive.org' in u for u in known[w]) and not has_arxiv(known[w]):
            targets.append((w, [f'dl.acm.org/doi/pdf/{d}', f'dl.acm.org/doi/pdf/{d}?download=true']))
    print(json.dumps(dict(wayback_acm_works=len(targets))), flush=True)
    rows, last = [], 0.0
    ev = F.FT / school / 'discovery' / f'claude-{school}-labpapers' / 'evidence'
    with log_f.open('a') as f:
        for k, (w, urls) in enumerate(targets):
            for url in urls:
                if url in done:
                    cap = done[url]
                else:
                    while True:
                        time.sleep(max(0, 8 - (time.monotonic() - last))); last = time.monotonic()
                        try:
                            r = s.get('https://web.archive.org/cdx/search/cdx', params=dict(url=url, output='json', fl='timestamp,original,mimetype,statuscode',
                                                                                           filter=['statuscode:200', 'mimetype:application/pdf'], limit=20), timeout=(15, 90))
                            status = r.status_code
                            caps = r.json()[1:] if status == 200 and r.text.strip() else []
                        except Exception as e:
                            status, caps = type(e).__name__, []
                        if not isinstance(status, int):  # the Archive refuses connections when throttling: back off, record nothing
                            print(json.dumps(dict(wayback_unreachable=status, pause_s=900)), flush=True); time.sleep(900); continue
                        if status == 429 or status >= 500:
                            time.sleep(120); continue
                        break
                    caps = [x for x in caps if 'casa_token' not in x[1] and 'cookieSet' not in x[1]]
                    best = max(caps, key=lambda x: x[0]) if caps else None
                    cap = dict(timestamp=best[0], original=best[1]) if best else None
                    done[url] = cap
                    f.write(json.dumps(dict(work_id=w, kind='acm', url=url, status=status, capture=cap, at=F.now())) + '\n'); f.flush()
                    n['wayback_lookups'] += 1
                if cap:
                    rows.append(dict(work_id=w, url=f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}", landing_url=None,
                                     version='publishedVersion', source='wayback_acm_dl', detail=url))
                    n['wayback_acm_hits'] += 1
                    break
            if len(rows) >= 50:  # write as we go: the lookups take hours
                n['candidates_added'] += write(school, new_rows(rows, known), 'wayback_acm', ev); rows = []
            if k % 200 == 199:
                print(json.dumps(dict(wayback_works=k + 1, of=len(targets), hits=n['wayback_acm_hits'])), flush=True)
    return rows


class Blocks:
    """HTML -> list of blocks (li, p, tr, dd, dt, td, div, section, article, h1-h6): each with its text and links, a
    parent's text including its children's."""
    TAGS = {'li', 'p', 'tr', 'dd', 'dt', 'td', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'table', 'body'}

    def __init__(self, body, base):
        from html.parser import HTMLParser
        from urllib.parse import urljoin
        self.blocks, stack = [], [dict(tag='root', text=[], links=[])]
        outer = self

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in Blocks.TAGS:
                    stack.append(dict(tag=tag, text=[], links=[]))
                if tag == 'a':
                    h = dict(attrs).get('href')
                    if h:
                        try:
                            stack[-1]['links'].append(urljoin(base, html.unescape(h.strip())))
                        except ValueError:
                            pass

            def handle_endtag(self, tag):
                if tag in Blocks.TAGS and len(stack) > 1:
                    # close up to the matching tag (HTML in the wild leaves tags open)
                    for i in range(len(stack) - 1, 0, -1):
                        if stack[i]['tag'] == tag:
                            while len(stack) > i:
                                b = stack.pop()
                                outer.blocks.append(b)
                                stack[-1]['text'] += b['text']; stack[-1]['links'] += b['links']
                            break

            def handle_data(self, data):
                stack[-1]['text'].append(data)

        p = P(convert_charrefs=True)
        try:
            p.feed(body); p.close()
        except Exception:
            pass
        while stack:
            b = stack.pop(); self.blocks.append(b)
            if stack:
                stack[-1]['text'] += b['text']; stack[-1]['links'] += b['links']
        for b in self.blocks:
            b['nt'] = F.nt(' '.join(b['text']))


def entry_links(blocks, title_nt, pdf_ok):
    """The PDF / arXiv links of the smallest block that contains the title and is one bibliography entry: at most
    ~1,500 normalized characters and exactly one distinct usable link (a PDF or an arXiv id)."""
    from cs_open_copies import arxiv_id
    best = None
    for b in blocks:
        if title_nt in b['nt'] and (best is None or len(b['nt']) < len(best['nt'])):
            best = b
    if not best or len(best['nt']) > max(1500, 3 * len(title_nt) + 600):
        return []
    links = []
    for u in dict.fromkeys(best['links']):
        a = arxiv_id(u)
        if a:
            links.append(('arxiv', re.sub(r'v\d+$', '', a)))
        elif pdf_ok(u):
            links.append(('pdf', u))
    kinds = {k for k, _ in links}
    pdfs = [l for l in links if l[0] == 'pdf']
    arx = {l[1] for l in links if l[0] == 'arxiv'}
    if len(pdfs) > 1 or len(arx) > 1:
        return []
    return links


def step_homepages(school, miss, known, n):
    """(berkeley) Author- and lab-hosted PDFs: each PI's own website (EECS directory 'website') and the websites of the
    units they lead (claude-berkeley-20261021 people/units.json), plus up to three pages those sites link as
    publications / papers; robots.txt honoured, one request per 3 s. A missing lab paper of that PI gains the one PDF
    (or arXiv id -> bulk copy) of the bibliography entry that carries its exact title."""
    assert school == 'berkeley'
    import requests, zlib
    from urllib.parse import urlsplit, urljoin
    import s2_key_lookup as s2k, core_search as cs
    BK = F.P.archive_sweep('claude-berkeley-20261021') / 'people'
    dept = json.loads((BK / 'dept_berkeley.json').read_text())
    units = json.loads((BK / 'units.json').read_text())['units']
    sites = defaultdict(list)
    for p in dept['people']:
        if p.get('website'):
            sites[F.nt(p['name'])].append(p['website'])
    for u in (units if isinstance(units, list) else units.values()):
        for lead in u.get('leads_as_listed') or []:
            sites[F.nt(lead)] += u.get('urls') or []
    by_pi = defaultdict(list)
    for r, w in miss:
        for pi in r.get('pis') or []:
            by_pi[pi].append((r, w))
    s = requests.Session(); s.headers['User-Agent'] = UA
    pacer, robots = Pacer(3.0), {}
    cache = sqlite3.connect(str(F.P.FT_RAW / 'homepages.sqlite'))
    cache.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, ok INT, fetched_at TEXT, body BLOB)')

    def get(url):
        row = cache.execute('SELECT ok, body FROM pages WHERE url=?', (url,)).fetchone()
        if row:
            return zlib.decompress(row[1]).decode('utf-8', 'replace') if row[0] else None
        body = polite_get(s, url, pacer, robots)
        cache.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?)', (url, int(body is not None), F.now(), zlib.compress((body or '').encode())))
        cache.commit()
        return body

    pdf_ok = lambda u: bool(re.search(r'\.pdf(?:$|[?#])', u, re.I)) and s2k.ok_pdf(u) and cs.usable(u) and u.startswith('http')
    rows, arx = [], {}
    for pi, items in sorted(by_pi.items()):
        roots = list(dict.fromkeys(re.sub(r'^http://', 'https://', u) for u in sites.get(F.nt(pi), [])))[:4]
        pages = []
        for root in roots:
            body = get(root)
            if body is None and root.startswith('https://'):
                root = 'http://' + root[len('https://'):]; body = get(root)
            if body is None:
                continue
            pages.append((root, body))
            host = urlsplit(root).hostname or ''
            subs = []
            for m in re.finditer(r'<a [^>]*href="([^"#]+)"[^>]*>(.*?)</a>', body, re.S | re.I):
                txt = re.sub(r'<[^>]+>', '', m.group(2)).strip().lower()
                if re.fullmatch(r'(?:selected |recent |all |full )?(?:publications?|papers|publication list|bibliography|research papers)(?: list)?', txt):
                    try:
                        u = urljoin(root, html.unescape(m.group(1)))
                    except ValueError:
                        continue
                    if (urlsplit(u).hostname or '').split('.')[-2:] == host.split('.')[-2:] and not re.search(r'\.(pdf|bib|ps|gz|zip)$', u, re.I):
                        subs.append(u)
            for u in list(dict.fromkeys(subs))[:3]:
                b = get(u)
                if b:
                    pages.append((u, b))
        n['homepage_pis_with_pages'] += bool(pages)
        n['homepage_pages'] += len(pages)
        for url, body in pages:
            blocks = Blocks(body, url).blocks
            for r, w in items:
                t = F.nt(r['title'])
                if len(t) < 25:
                    continue
                for kind, v in entry_links(blocks, t, pdf_ok):
                    if kind == 'arxiv':
                        if not has_arxiv(known[w]):
                            arx[w] = v
                    else:
                        rows.append(dict(work_id=w, url=v, landing_url=url, version=None, source='author_or_lab_site', detail=pi))
                        n['homepage_pdf_links'] += 1
    brows, n['homepage_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'author_or_lab_site_arxiv_bulk')
    n['homepage_arxiv'] = len(brows)
    return rows + brows


def step_infoscience(school, miss, known, n):
    """(epfl) Infoscience handles among the lab works' known links -> the REST API's ORIGINAL PDF files
    (../../claude-epfl-20261019/tools/epfl_infoscience_rest.py resolve + add, restricted to these works; 3 s per
    request; an empty 202 / 429 / 503 pauses it and is never worked around). It writes its own candidates."""
    assert school == 'epfl'
    sys.path.insert(0, str(F.P.vendor('epfl_tools')))
    import epfl_infoscience_rest as eir
    handles = {}
    for r, w in miss:
        for u in known[w]:
            m = eir.HANDLE.match(u)
            if m:
                handles.setdefault(w, set()).add(m.group(1))
    n['infoscience_lab_works_with_handle'] = len(handles)
    kn = {w: set(known[w]) for w in handles}
    eir.resolve(handles, kn)
    eir.add(handles, kn)
    for w, us in kn.items():
        n['infoscience_candidates'] += len(us - known[w])
        known[w] |= us
    return []


def step_proceedings(school, miss, known, n):
    """Open proceedings (the Princeton sweep's index of NeurIPS, PMLR, ICLR, CVF, ACL Anthology, IJCAI, USENIX, JMLR,
    PVLDB, ECCC, RSS, ...: claude-princeton-20261015/cs-structure/raw/proceedings/index.json.gz): an entry whose
    normalized title equals the paper's (>= 20 characters) and whose year is within 2 -> its PDF on the open host."""
    import gzip
    import s2_key_lookup as s2k
    idx = defaultdict(list)
    src = F.P.archive_sweep('claude-princeton-20261015') / 'cs-structure/raw/proceedings/index.json.gz'
    for t, y, u, land, venue in json.loads(gzip.decompress(src.read_bytes())):
        k = F.nt(t)
        if len(k) >= 20:
            idx[k].append((y, u, land, venue))
    rows = []
    for r, w in miss:
        for y, u, land, venue in idx.get(F.nt(r['title']), []):
            if (not r.get('year') or not y or abs(int(y) - int(r['year'])) <= 2) and s2k.ok_pdf(u):
                rows.append(dict(work_id=w, url=u, landing_url=land, version='publishedVersion', source='open_proceedings_index', detail=venue))
                n['proceedings:' + re.sub(r'\d{4}(\.py)?$', '', venue or '')] += 1
    return rows


def step_europepmc(school, miss, known, n):
    """Europe PMC's REST search (25 DOIs per query, one query per 10 s as its robots.txt asks; cached in the CMU stage's
    raw/europepmc.jsonl) for the lab papers' DOIs: a hit with a PMCID -> its files in NLM's PMC open-data dataset on
    S3 (PDF before JATS XML), through ../../claude-cmu-20261017/tools/europepmc_lookup.py search / files."""
    import requests
    import europepmc_lookup as ep
    dois = {}
    for r, w in miss:
        d = F.ndoi(r.get('doi'))
        if d and not d.startswith('10.48550/') and not any('pmc-oa-opendata' in u for u in known[w]):
            dois.setdefault(d, []).append(w)
    done = ep.search(list(dois))
    s = requests.Session(); s.headers['User-Agent'] = UA
    memo, rows = {}, []
    for d, ws in dois.items():
        pmcid = (done.get(d) or {}).get('pmcid')
        if not pmcid:
            continue
        n['europepmc_with_pmcid'] += 1
        for u in ep.files(s, pmcid, memo):
            for w in ws:
                rows.append(dict(work_id=w, url=u, landing_url=f'https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/', version=None, source='europepmc_pmc_open_data', detail=pmcid))
    return rows


def step_dspace(school, miss, known, n):
    """(mit) DSpace@MIT handles among the lab works' known links -> the items' ORIGINAL PDFs through OAI-PMH ORE
    records (one request per 8 s; robots.txt leaves /server/oai open) -> REST bitstream URLs
    (../../claude-mit-20261020/tools/mit_dspace_rest.py resolve + add, restricted to these works). It writes its own
    candidates; the web front end (rate-limited) is never used."""
    assert school == 'mit'
    sys.path.insert(0, str(F.P.vendor('mit_tools')))
    import mit_dspace_rest as mds
    handles = {}
    for r, w in miss:
        for u in known[w]:
            m = mds.HANDLE.match(u)
            if m:
                handles.setdefault(w, set()).add(m.group(1))
    n['dspace_lab_works_with_handle'] = len(handles)
    kn = {w: set(known[w]) for w in handles}
    mds.resolve(handles, kn, batch=100)
    mds.add(handles, kn)
    for w, us in kn.items():
        n['dspace_candidates'] += len(us - known[w])
        known[w] |= us
    return []


def step_labpages(school, miss, known, n):
    import labpage_channel as lc
    return lc.step_labpages(school, miss, known, n, has_arxiv)


def step_pihomes(school, miss, known, n):
    import labpage_channel as lc
    return lc.step_pihomes(school, miss, known, n, has_arxiv)


def step_oar(school, miss, known, n):
    import repo_index
    return repo_index.step_oar(school, miss, known, n)


STEPS = dict(oar=step_oar, labpages=step_labpages, pihomes=step_pihomes, oa_arxiv=step_oa_arxiv, openalex=step_openalex, arxiv_title=step_arxiv_title, s2=step_s2, core=step_core, pmc=step_pmc,
             figshare=step_figshare, techrpt=step_techrpt, pubpages=step_pubpages, wayback_acm=step_wayback_acm,
             homepages=step_homepages, infoscience=step_infoscience,
             proceedings=step_proceedings, europepmc=step_europepmc, dspace=step_dspace)


# 2026-10-29 additions (new modules; the steps above are unchanged):
#   dblp_ee      DBLP dump electronic editions + CoRR twins (dblp_ee.py)
#   oa_refresh   OpenAlex records re-read 50 ids per request; arXiv edition DOIs (oa_refresh.py)
#   oa_editions  OpenAlex title search for separate open editions, budget-guarded (oa_refresh.py)
#   s2_title     Semantic Scholar /paper/search/match for papers the DOI batch could not use (s2_title.py)
def step_dblp_ee(school, miss, known, n):
    import dblp_ee
    return dblp_ee.step(school, miss, known, n, has_arxiv)


def step_oa_refresh(school, miss, known, n):
    import oa_refresh
    return oa_refresh.step_oa_refresh(school, miss, known, n, has_arxiv)


def step_oa_editions(school, miss, known, n):
    import oa_refresh
    return oa_refresh.step_oa_editions(school, miss, known, n, has_arxiv)


def step_s2_title(school, miss, known, n):
    import s2_title
    return s2_title.step(school, miss, known, n, has_arxiv)


STEPS.update(dblp_ee=step_dblp_ee, oa_refresh=step_oa_refresh, oa_editions=step_oa_editions, s2_title=step_s2_title)


# ---------------------------------------------------------------- negatives (2026-10-30, owner; docs/UNAVAILABLE.md)
# Every step records one check per paper it examined into fulltext-push/checks/<school>.sqlite (checks.py): 'found' with
# the URLs it produced, else 'none' (channels/legacy.py turns a step's outcome into Results; channel_runner.py records
# them). A paper is examined when it is in the step's scope below (the query names what was asked); a step that stopped
# early on a budget or on repeated failures records 'error' for the papers it did not find.
_ARX = lambda k: has_arxiv(k)
_DOI = lambda r: F.ndoi(r.get('doi'))
_T = lambda r: r.get('title') if len(F.nt(r.get('title'))) >= 20 else None
_OA = lambda r: F.oa_short(r.get('oa')) or None
SCOPE = dict(
    oa_arxiv=lambda s, r, k: None if _ARX(k) else (f'arXiv id of {_OA(r)} (DOI / OpenAlex locations)' if _OA(r) else None),
    openalex=lambda s, r, k: _OA(r) and f'OpenAlex locations of {_OA(r)}',
    oa_refresh=lambda s, r, k: _OA(r) and f'OpenAlex record refreshed: {_OA(r)}',
    oa_editions=lambda s, r, k: _T(r) and f'OpenAlex open editions by title: {_T(r)}',
    arxiv_title=lambda s, r, k: None if _ARX(k) else (_T(r) and f'arXiv OAI index title: {_T(r)}'),
    s2=lambda s, r, k: (f'DOI:{_DOI(r)}' if _DOI(r) else (f'ARXIV:{F.arxiv_of(r, None)}' if F.arxiv_of(r, None) else None)),
    s2_title=lambda s, r, k: None if (_DOI(r) or F.arxiv_of(r, None)) else (_T(r) and f'S2 search/match: {_T(r)}'),
    core=lambda s, r, k: _DOI(r) and not _DOI(r).startswith('10.48550/') and f'CORE doi:{_DOI(r)}',
    europepmc=lambda s, r, k: _DOI(r) and not _DOI(r).startswith('10.48550/') and not any('pmc-oa-opendata' in u for u in k) and f'Europe PMC DOI:{_DOI(r)}',
    pmc=lambda s, r, k: any(F.PMC_LINK.search(u) for u in k) and 'PMC links among known URLs',
    figshare=lambda s, r, k: (any(re.search(r'figshare|kilthub', u) for u in k) or _DOI(r).startswith(('10.6084/', '10.1184/'))) and 'Figshare / KiltHub article files',
    dblp_ee=lambda s, r, k: (_DOI(r) or _T(r)) and f'DBLP dump ee: {_DOI(r) or _T(r)}',
    proceedings=lambda s, r, k: _T(r) and f'open proceedings index title: {_T(r)}',
    labpages=lambda s, r, k: f"lab-page captures of {', '.join(r.get('pis') or [])}",
    pihomes=lambda s, r, k: f"PI homepages of {', '.join(r.get('pis') or [])}",
    oar=lambda s, r, k: s == 'princeton' and f'Princeton OAR index: {_DOI(r) or _T(r)}',
    techrpt=lambda s, r, k: s == 'berkeley' and _T(r) and f'EECS technical reports title: {_T(r)}',
    pubpages=lambda s, r, k: s == 'berkeley' and _T(r) and f'EECS faculty publications pages title: {_T(r)}',
    homepages=lambda s, r, k: s == 'berkeley' and _T(r) and f"author / lab sites of {', '.join(r.get('pis') or [])}",
    wayback_acm=lambda s, r, k: _DOI(r).startswith('10.1145/') and not any('web.archive.org' in u for u in k) and not _ARX(k)
    and f'Wayback CDX dl.acm.org/doi/pdf/{_DOI(r)}',
    infoscience=lambda s, r, k: any('infoscience.epfl.ch' in u for u in k) and 'Infoscience REST files of the known handles',
    dspace=lambda s, r, k: any(re.search(r'hdl\.handle\.net/1721\.1/|dspace\.mit\.edu', u) for u in k) and 'DSpace@MIT files of the known handles',
)


def write(school, rows, step, ev_dir=None, dry=False):
    if dry or not rows:
        return 0
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    if school == 'princeton':
        pkg = F.FT / 'princeton' / 'discovery' / f'claude-labpapers-{step}-{stamp}'
        (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
        ev = pkg / 'evidence' / f'{step}.json'
        ev.write_text(json.dumps(dict(rule=__doc__, created_at=F.now(), rows=rows)))
        with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
            for r in rows:
                f.write(json.dumps(dict(work_id=r['work_id'], url=r['url'], landing_url=r.get('landing_url'), license=r.get('license'), version=r.get('version'),
                                        metadata_source=str(ev), source=r['source'], detail=r.get('detail'))) + '\n')
        (pkg / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in rows)) + '\n')
        (pkg / 'summary.json').write_text(json.dumps(dict(created_at=F.now(), counts=dict(Counter(r['source'] for r in rows)),
                                                          works_gaining_candidate=len({r['work_id'] for r in rows}), requires_packages=[], rules=__doc__), indent=1))
        return len(rows)
    ev_dir = ev_dir or F.FT / school / 'discovery' / f'claude-{school}-labpapers' / 'evidence'
    return F.write_candidates(school, rows, ev_dir / f'{step}-{stamp}.json', __doc__)


def main():
    """Since 2026-10-30 a thin wrapper: every step runs as a channel plugin (channels/<step>.py) through the one runner
    (channel_runner.py: known-URL filtering, candidate writes, the per-paper checks, the channels.jsonl line)."""
    import channel_runner
    channel_runner.main(sys.argv[1:])


if __name__ == '__main__':
    main()
