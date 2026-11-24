"""More title sources for the lab-paper copies still pending on identity (ROADMAP #25 follow-up, 2026-11-03, owner).

The pending copies (identity_check provider_link_only_review_pending, status downloaded; copies.json status identity_unconfirmed) were
judged against every title the caches hold (OpenAlex, snapshot, S2 cache, the arXiv OAI title, the PDF metadata). This module adds
titles that no cache had, each fetched once and cached in raw/identity_titles.jsonl:
  crossref  api.crossref.org/works/<doi>: the title (and 'title: subtitle') the publisher deposited for the work's own DOI
            (polite: one request per second, a user agent without an address)
  arxiv     arxiv.org/abs/<id>v1 and /abs/<id> (robots.txt allows /abs, Crawl-delay 15 s; export.arxiv.org is disallowed and is not used):
            the first and the latest version's title, for the arXiv id the work's DOI or OpenAlex record maps to
  s2        Semantic Scholar /paper/batch by DOI (the user's key from the environment, one request per 1.2 s through s2_key_lookup) for DOIs
            the S2 cache has no record of
A copy passes only under the rule's own bar (identity_rule.judge on the new title, the first authoritative author or the DOI on page 1;
the metadata path through judge_meta) and the apply rules of identity_review.apply_alt: the matched title shares 80% of the shorter
title's words with the catalog title unless the DOI is an arXiv DOI (own_doi_title_ok), no deposit DOI, no arXiv title for a work without a DOI.
Tag auto_alt_title_20261103. Nothing is rejected here (a pass or it stays pending).
usage: identity_title_sources.py fetch|plan|apply|rollback <school> ... [--limit N]
  fetch     network: fills the cache for the school's pending lab-paper copies (read-only on the catalogs)
  plan      cache only: judges, writes review-20261030/identity-review-titles-<school>.json
  apply     locked catalog backup, then identity_check <- tag for the passes (catalog_lock); logged in <store>/staged/identity-titles-20261103.jsonl
  rollback  every work carrying the tag goes back to pending (the source is withdrawn after a failed hand check)
"""
import json, os, re, sqlite3, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ftp_common as F  # noqa: E402
import identity_review as IR  # noqa: E402
import identity_rule as R  # noqa: E402

TAG = 'auto_alt_title_20261103'
PENDING = R.PENDING
CACHE = F.P.FT_RAW / 'identity_titles.jsonl'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
DEPOSIT = ('10.5281/', '10.6084/', '10.17605/', '10.5061/', '10.7910/')
_C = {}


def cache():
    if not _C:
        for line in open(CACHE) if CACHE.exists() else []:
            try:
                r = json.loads(line)
                _C[(r['kind'], r['key'])] = r
            except ValueError:
                pass
    return _C


def put(kind, key, titles, status, extra=None):
    r = dict(kind=kind, key=key, at=F.now(), status=status, titles=titles, **(extra or {}))
    with open(CACHE, 'a') as f:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
    _C[(kind, key)] = r


def pending_lab(school):
    """{catalog id: row} of the lab-paper copies counted identity_unconfirmed whose catalog work is still pending."""
    cop = json.loads(F.P.data('copies.json', school).read_text())['papers']
    ids = sorted({c['catalog'] for c in cop.values() if c.get('status') == 'identity_unconfirmed' and c.get('catalog')})
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    out = {}
    for k in range(0, len(ids), 400):
        part = ids[k:k + 400]
        q = ','.join('?' * len(part))
        for i, fp, du, title, doi, g, oaj, ic, st in db.execute(
                f'SELECT id, file_path, download_url, title, doi, graph_json, oa_json, identity_check, status FROM works WHERE id IN ({q})', part):
            if ic == PENDING and st == 'downloaded' and fp:
                out[i] = dict(file_path=fp, download_url=du, title=title, doi=F.ndoi(doi), graph=g, oa_json=oaj)
    db.close()
    return out


def arxiv_ids(school, rows):
    """{work: arXiv id}: the work's arXiv DOI, else the id the S2 / OpenAlex caches map its DOI to (works with a DOI only)."""
    import s2_key_lookup as s2k
    out = {}
    papers = F.lab_papers(school)
    oa = {}
    for r in papers.values():
        for k in (r.get('work'), F.oa_work_id(school, r)):
            if k:
                oa[k] = r.get('oa')
    for w, c in rows.items():
        d = c['doi']
        if not d:
            continue
        if d.startswith('10.48550/arxiv.'):
            out[w] = d.split('arxiv.', 1)[1]
            continue
        a = R.mapped_arxiv(d, s2k.CACHE, F.P.FT_RAW / 'ledger_openalex.jsonl', oa.get(w))
        if a:
            out[w] = re.sub(r'v\d+$', '', a)
    return out


def fetch(school, limit=None):
    import requests
    rows = pending_lab(school)
    ws = list(rows)[:limit] if limit else list(rows)
    s = requests.Session()
    s.headers['User-Agent'] = UA
    n = Counter()
    # crossref: one request per second, by the work's own DOI (arXiv DOIs are DataCite: not asked)
    for w in ws:
        d = rows[w]['doi']
        if not d or d.startswith('10.48550/') or ('crossref', d) in cache():
            continue
        for attempt in range(4):
            try:
                r = s.get('https://api.crossref.org/works/' + requests.utils.quote(d, safe='/'), timeout=(15, 60))
            except Exception as e:
                time.sleep(10 * (attempt + 1)); err = str(e)[:100]; continue
            if r.status_code == 200:
                m = r.json().get('message') or {}
                ts = []
                for t in (m.get('title') or []) + (m.get('original-title') or []):
                    ts.append(t)
                    for sub in (m.get('subtitle') or [])[:1]:
                        ts.append(f'{t}: {sub}')
                put('crossref', d, [' '.join(re.sub(r'<[^>]+>', ' ', t).split()) for t in ts], 'ok', dict(type=m.get('type'), container=(m.get('container-title') or [None])[0]))
                n['crossref_ok'] += 1
                break
            if r.status_code == 404:
                put('crossref', d, [], 'not_found'); n['crossref_404'] += 1; break
            time.sleep(10 * (attempt + 1))
        time.sleep(1.0)
    # arxiv: abs pages (robots allows /abs; Crawl-delay 15 s): v1 and the latest
    ax = arxiv_ids(school, {w: rows[w] for w in ws})
    for w, a in ax.items():
        for ver in ('v1', ''):
            key = a + ver
            if ('arxiv', key) in cache():
                continue
            time.sleep(15)
            try:
                r = s.get(f'https://arxiv.org/abs/{key}', timeout=(15, 60))
            except Exception:
                continue
            if r.status_code == 200:
                m = re.search(r'<meta name="citation_title" content="([^"]*)"', r.text)
                import html
                put('arxiv', key, [' '.join(html.unescape(m.group(1)).split())] if m else [], 'ok'); n['arxiv_ok'] += 1
            elif r.status_code == 404:
                put('arxiv', key, [], 'not_found')
            elif r.status_code in (429, 503):
                time.sleep(120)
    # s2: DOIs the S2 cache has no record of
    import s2_key_lookup as s2k
    have = IR.alt_title_sources()['s2']
    miss = sorted({rows[w]['doi'] for w in ws if rows[w]['doi'] and rows[w]['doi'] not in have and ('s2', rows[w]['doi']) not in cache()})
    if miss and os.environ.get('S2_API_KEY'):
        s.headers['x-api-key'] = os.environ['S2_API_KEY']
        for k in range(0, len(miss), 100):
            part = miss[k:k + 100]
            r = s2k.s2(s, 'POST', '/paper/batch?fields=title,externalIds', json={'ids': ['DOI:' + d for d in part]})
            if r is not None and r.status_code == 200:
                for d, rec in zip(part, r.json()):
                    put('s2', d, [rec['title']] if rec and rec.get('title') else [], 'ok' if rec else 'not_found',
                        dict(arxiv=(rec or {}).get('externalIds', {}).get('ArXiv')))
                    n['s2_ok' if rec else 's2_none'] += 1
    print(json.dumps(dict(school=school, pending=len(rows), fetched_for=len(ws), **n)), flush=True)


def plan(school):
    import shutil
    if not shutil.which('pdftotext'):
        raise SystemExit('pdftotext is not on PATH')
    store = F.FT / school
    rows = pending_lab(school)
    ax = arxiv_ids(school, rows)
    out, n = [], Counter()
    for w, c in rows.items():
        p = store / c['file_path']
        if not p.exists():
            n['file_missing'] += 1
            continue
        d = c['doi']
        alts = []
        if d and ('crossref', d) in cache():
            alts += [(t, 'Crossref (the work\'s own DOI)') for t in cache()[('crossref', d)]['titles']]
        if d and ('s2', d) in cache():
            alts += [(t, 'Semantic Scholar (DOI batch)') for t in cache()[('s2', d)]['titles']]
        if d and w in ax:  # an arXiv title only for a work with a DOI of its own (identity_review.apply_alt)
            for ver in ('v1', ''):
                for t in (cache().get(('arxiv', ax[w] + ver)) or {}).get('titles', []):
                    alts.append((t, f'arXiv {ax[w]}{ver or " (latest)"} listing'))
        seen, alt2 = set(), []
        for t, how in alts:
            k = F.nt(t)
            if k and k != F.nt(c['title']) and k not in seen:
                seen.add(k); alt2.append((t, how))
        p1, p12 = R.page_text(p, 1, 1), R.page_text(p, 1, 2)
        first, auth = R.first_author(F.SCHOOLS, school, w, c['title'], d, graph_json=c['graph'])
        meta = R.pdf_meta_title(p)
        hit = None
        for t, how in alt2:
            if len([x for x in R.norm_words(t) if len(x) >= 3 and x not in R.STOP]) < 3:
                continue
            v, ev = R.judge(p1, t, first, d, c['download_url'], None, p12=p12, author_authoritative=auth)
            if v == 'pass_title' and R.own_doi_title_ok(d, c['title'], t) and not d.startswith(DEPOSIT):
                hit = (t, how, ev, 'pass_alt'); break
        if not hit and alt2:
            mv, mev = R.judge_meta(meta, [c['title']] + [t for t, _ in alt2], p1, first if auth else '', d)
            if mv == 'pass_meta' and R.own_doi_title_ok(d, c['title'], mev['matched_title']) and not d.startswith(DEPOSIT):
                hit = (mev['matched_title'], 'PDF metadata title vs a new title', mev, 'pass_meta')
        n['pass' if hit else ('undecided_new_titles' if alt2 else 'no_new_title')] += 1
        out.append(dict(work=w, verdict=hit[3] if hit else 'undecided', title=c['title'], doi=d, alt_title=hit[0] if hit else None,
                        alt_source=hit[1] if hit else None, new_titles=alt2[:4], page1=re.sub(r'\s+', ' ', p1)[:400], meta_title=meta,
                        file=c['file_path'], **({k: v for k, v in hit[2].items() if k in ('title_words_found', 'author_on_page1', 'doi_on_page1', 'first_author')} if hit else {})))
    IR.OUT.mkdir(exist_ok=True)
    (IR.OUT / f'identity-review-titles-{school}.json').write_text(json.dumps(dict(school=school, at=F.now(), rows=out), indent=0, ensure_ascii=False))
    print(json.dumps(dict(school=school, pending=len(rows), **n)), flush=True)


def apply(school):
    store = F.FT / school
    rows = json.loads((IR.OUT / f'identity-review-titles-{school}.json').read_text())['rows']
    passes = [x for x in rows if x['verdict'].startswith('pass')]
    if not passes:
        print(json.dumps(dict(school=school, confirmed=0))); return
    F.backup_catalog(store, 'before-identity-titles-20261103')
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    n = Counter()
    log = store / 'staged' / 'identity-titles-20261103.jsonl'
    log.parent.mkdir(exist_ok=True)
    for x in passes:
        with F.catalog_lock(store):
            c = db.execute('UPDATE works SET identity_check=? WHERE id=? AND identity_check=?', (TAG, x['work'], PENDING)).rowcount
            db.execute('UPDATE assets SET identity_check=? WHERE work_id=? AND identity_check=?', (TAG, x['work'], PENDING))
            db.commit()
        n['confirmed'] += c
        if c:
            with open(log, 'a') as f:
                f.write(json.dumps(dict(work=x['work'], at=F.now(), tag=TAG, alt_title=x['alt_title'], alt_source=x['alt_source'], title=x['title'])) + '\n')
    db.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


def rollback(school, works=None):
    """Every work with the tag (or only `works`) back to pending: the source is withdrawn."""
    store = F.FT / school
    F.backup_catalog(store, 'before-identity-titles-rollback')
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    n = Counter()
    ids = [r[0] for r in db.execute('SELECT id FROM works WHERE identity_check=?', (TAG,))]
    for w in ids:
        if works and w not in works:
            continue
        with F.catalog_lock(store):
            n['reverted'] += db.execute('UPDATE works SET identity_check=? WHERE id=? AND identity_check=?', (PENDING, w, TAG)).rowcount
            db.execute('UPDATE assets SET identity_check=? WHERE work_id=? AND identity_check=?', (PENDING, w, TAG))
            db.commit()
    db.close()
    print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    if lim is not None:
        args = [a for a in args if a != str(lim)]
    cmd, schools = args[0], args[1:]
    for s in schools:
        {'fetch': lambda x: fetch(x, lim), 'plan': plan, 'apply': apply, 'rollback': rollback}[cmd](s)
