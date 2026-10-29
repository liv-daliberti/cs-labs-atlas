"""dblp_ee step (2026-10-29): DBLP electronic editions for lab papers without a copy, from DBLP's official monthly dump
on Dagstuhl DROPS (var/data/dblp-dump/dblp-2026-09-01.xml.gz; never the bot-walled dblp.org site).

scan   one streaming pass over the dump (records matched whole, as tools/dblp_dump_index.py does). For every lab paper
       without a copy at the six schools (local-reuse/missing.jsonl.gz plus the step's own list):
         a venue record with the paper's DOI (an <ee> doi.org link), or with its normalized title (>= 20 characters,
         year within 1) and a shared author family name -> the record's <ee> links
         a CoRR record (journals/corr/) with the paper's normalized title, a shared author family name and a year from
         3 before to 1 after the paper's -> its arXiv id
       -> raw/dblp_ee_matches.jsonl.gz (one row per paper key and record)
step   the cached matches -> candidates: arXiv ids -> arXiv's bulk copy on GCS (as oa_arxiv; never arxiv.org);
       <ee> links on open proceedings / repository hosts (OPEN_HOSTS), rewritten to the PDF where the host's layout is
       fixed (aclanthology, ijcai, openreview), else the landing page (the collector follows its citation_pdf_url);
       doi.org links only for open-access DOI prefixes (OPEN_DOI). Publisher hosts (IEEE, ACM, Springer, Elsevier, ...)
       are never added. The collector's robots.txt check, per-host pacing and identity check apply as for every candidate.
usage: dblp_ee.py scan     (the step itself runs through lab_channels.py <school> dblp_ee)
"""
import gzip, html, json, re, sys, time, unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F

DUMP = Path('/n/fs/resemble/maxent-grpo/var/data/dblp-dump/dblp-2026-09-01.xml.gz')
CACHE = HERE / 'raw' / 'dblp_ee_matches.jsonl.gz'
REC = re.compile(r'<(article|inproceedings|proceedings|book|incollection|phdthesis|mastersthesis|www|data) [^>]*?key="([^"]+)"[^>]*>(.*?)</\1>', re.S)
EE = re.compile(r'<ee[^>]*>([^<]+)</ee>')
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S)
AUTHOR = re.compile(r'<author[^>]*>([^<]+)</author>')
YEAR = re.compile(r'<year>(\d{4})</year>')
OPEN_HOSTS = ('aclanthology.org', 'www.aclweb.org', 'openaccess.thecvf.com', 'proceedings.mlr.press', 'jmlr.org', 'www.jmlr.org',
              'www.usenix.org', 'usenix.org', 'www.ndss-symposium.org', 'ndss-symposium.org', 'ojs.aaai.org', 'www.ijcai.org', 'ijcai.org',
              'www.vldb.org', 'vldb.org', 'ceur-ws.org', 'papers.nips.cc', 'proceedings.neurips.cc', 'papers.neurips.cc', 'openreview.net',
              'drops.dagstuhl.de', 'www.roboticsproceedings.org', 'roboticsproceedings.org', 'www.isca-speech.org', 'www.isca-archive.org',
              'eprint.iacr.org', 'www.jair.org', 'jair.org', 'www.ifaamas.org', 'ifaamas.org', 'www.ecva.net', 'ecva.net', 'eccc.weizmann.ac.il',
              'www.bmva.org', 'bmva-archive.org.uk', 'www.cv-foundation.org', 'lmcs.episciences.org', 'theoryofcomputing.org', 'www.theoryofcomputing.org',
              'cdn.aaai.org', 'tmlr.org', 'jfr.org', 'www.jfr.org', 'transacl.org', 'www.semantic-web-journal.net', 'ieeevis.org', 'www.ndss-symposium.org',
              'ml4h.cc', 'arxiv.org')
OPEN_DOI = ('10.18653/', '10.4230/', '10.21437/', '10.24963/', '10.14778/', '10.15607/', '10.1609/', '10.5281/', '10.46298/', '10.4086/',
            '10.1162/tacl', '10.1613/jair', '10.29007/', '10.5220/', '10.2312/')


def nt(t):
    return F.nt(html.unescape(re.sub(r'<[^>]+>', '', t or '')))


def fam(name):
    toks = [re.sub(r'[^a-z]', '', t) for t in unicodedata.normalize('NFKD', re.sub(r'\s\d{4}$', '', name or '')).encode('ascii', 'ignore').decode().lower().split()]
    toks = [t for t in toks if t and t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return toks[-1] if toks and len(toks[-1]) >= 3 else ''


def targets(extra=()):
    rows = []
    p = HERE / 'local-reuse' / 'missing.jsonl.gz'
    if p.exists():
        rows += [json.loads(l) for l in gzip.open(p, 'rt')]
    rows += list(extra)
    by_doi, by_title = defaultdict(list), defaultdict(list)
    for r in rows:
        t = dict(key=r['key'], year=r.get('year'), fam={fam(n) for n in (r.get('byline') or []) + (r.get('pis') or [])} - {''})
        for d in [r.get('doi')] + list(r.get('editions') or []):
            if d:
                by_doi[F.ndoi(d)].append(t)
        k = nt(r.get('title'))
        if len(k) >= 20:
            by_title[k].append(t)
    return by_doi, by_title


def scan(extra=()):
    by_doi, by_title = targets(extra)
    print(json.dumps(dict(dois=len(by_doi), titles=len(by_title))), flush=True)
    n, hits, tail, t0 = 0, 0, '', time.time()
    tmp = CACHE.with_suffix('.part')
    with gzip.open(DUMP, 'rt', encoding='utf-8', errors='replace') as f, gzip.open(tmp, 'wt') as out:
        while True:
            chunk = f.read(16 << 20)
            buf = tail + chunk
            end = 0
            for m in REC.finditer(buf):
                end = m.end(); n += 1
                typ, key, body = m.groups()
                if typ in ('www', 'data') or key.startswith(('homepages/', 'data/')):
                    continue
                corr = key.startswith('journals/corr/')
                ees = [html.unescape(e).strip() for e in EE.findall(body)]
                dois = {F.ndoi(e) for e in ees if re.match(r'https?://(?:dx\.)?doi\.org/', e)}
                tm = TITLE.search(body)
                k = nt(tm.group(1)) if tm else ''
                ym = YEAR.search(body)
                year = int(ym.group(1)) if ym else None
                fams = None
                found = []
                if not corr:
                    for d in dois:
                        for t in by_doi.get(d, []):
                            found.append((t, 'doi'))
                for t in by_title.get(k, []) if len(k) >= 20 else []:
                    if fams is None:
                        fams = {fam(html.unescape(a)) for a in AUTHOR.findall(body)} - {''}
                    if not (t['fam'] & fams):
                        continue
                    if t['year'] and year:
                        lo, hi = (t['year'] - 3, t['year'] + 1) if corr else (t['year'] - 1, t['year'] + 1)
                        if not lo <= year <= hi:
                            continue
                    found.append((t, 'corr_title' if corr else 'title'))
                seen = set()
                for t, rule in found:
                    if (t['key'], key) in seen:
                        continue
                    seen.add((t['key'], key)); hits += 1
                    out.write(json.dumps(dict(paper=t['key'], dblp_key=key, rule=rule, year=year, ee=ees)) + '\n')
            if not chunk:
                break
            tail = buf[end:] if end else buf
            if len(tail) > (64 << 20):
                tail = tail[-(1 << 20):]
            if n and n % 500000 < 20000:
                pass
        print(json.dumps(dict(records=n, hits=hits, seconds=round(time.time() - t0))), flush=True)
    tmp.replace(CACHE)


def open_url(u):
    """An <ee> link -> a URL the collector may fetch (PDF where the host's layout is fixed), or None."""
    from urllib.parse import urlsplit
    u = u.strip()
    if re.match(r'https?://(?:dx\.)?doi\.org/', u):
        d = F.ndoi(u)
        if d.startswith('10.18653/v1/'):
            return f'https://aclanthology.org/{d.split("/v1/", 1)[1].upper()}.pdf'
        return 'https://doi.org/' + d if d.startswith(OPEN_DOI) else None
    u = re.sub(r'^http://', 'https://', u)
    h = (urlsplit(u).hostname or '').lower()
    if h not in OPEN_HOSTS or h == 'arxiv.org':
        return None
    if h in ('aclanthology.org', 'www.aclweb.org'):
        m = re.search(r'/([A-Z0-9][A-Za-z0-9.\-]+?)(?:\.pdf)?/?$', u)
        return f'https://aclanthology.org/{m.group(1)}.pdf' if m else u
    if h in ('www.ijcai.org', 'ijcai.org'):
        m = re.search(r'/proceedings/(\d{4})/(\d+)/?$', u)
        return f'https://www.ijcai.org/proceedings/{m.group(1)}/{m.group(2)}.pdf' if m else u
    if h == 'openreview.net':
        m = re.search(r'[?&]id=([^&#]+)', u)
        return f'https://openreview.net/pdf?id={m.group(1)}' if m else None
    return u


def arxiv_from(ees):
    for e in ees:
        m = re.search(r'arxiv\.org/abs/([^\s?#]+)', e) or re.search(r'doi\.org/10\.48550/arxiv\.([^\s?#]+)', e, re.I)
        if m:
            return re.sub(r'v\d+$', '', m.group(1))
    return None


def step(school, miss, known, n, has_arxiv):
    if not CACHE.exists():
        scan([dict(key=r['work'] or r['oa'], doi=r.get('doi'), editions=[e.get('doi') for e in r.get('editions') or [] if e.get('doi')],
                   title=r.get('title'), year=r.get('year'), byline=r.get('byline'), pis=r.get('pis')) for r, _ in miss])
    by_paper = defaultdict(list)
    for l in gzip.open(CACHE, 'rt'):
        x = json.loads(l); by_paper[x['paper']].append(x)
    rows, arx = [], {}
    for r, w in miss:
        for x in by_paper.get(r['work'] or r['oa'], []):
            n['dblp_records:' + x['rule']] += 1
            a = arxiv_from(x['ee'])
            if a:
                if not has_arxiv(known[w]):
                    arx[w] = a
                continue
            for e in x['ee']:
                u = open_url(e)
                if u:
                    rows.append(dict(work_id=w, url=u, landing_url=e, version='publishedVersion', source='dblp_ee', detail=x['dblp_key']))
    n['dblp_ee_links'] = len(rows)
    brows, n['dblp_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'dblp_corr_arxiv_bulk')
    n['dblp_arxiv_bulk'] = len(brows)
    return rows + brows


if __name__ == '__main__':
    {'scan': scan}[sys.argv[1]]()
