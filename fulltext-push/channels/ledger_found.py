"""Channel ledger_found (2026-10-30): open copies the unavailability ledger's own checks found that are not candidates
yet (hierarchy/<school>/unavailable.jsonl.gz, field new_open_urls; docs/UNAVAILABLE.md). Each source's rules already
decided what is usable (OpenAlex locations as the openalex step, S2 openAccessPdf / ArXiv / PMC ids, CORE repository
links, DBLP ee on open hosts, the open proceedings, the school repository, the PI's lab pages, Wayback ACM captures):
  arXiv:<id>  -> arXiv's bulk copy on GCS (ftp_common.bulk_rows; never arxiv.org)
  PMC<id>     -> the PMC open-data files on S3 (s2_key_lookup.pmc_files)
  a URL       -> itself, on a host the collectors may use (s2_key_lookup.ok_pdf and core_search.usable)
The collector's robots.txt check (with its AI-crawler groups), pacing and title check apply as for every candidate.
"""
import gzip
import json

NAME = 'ledger_found'
_CACHE = {}


def ledger(school):
    if school not in _CACHE:
        import ftp_common as F
        p = F.SCHOOLS / 'hierarchy' / school / 'unavailable.jsonl.gz'
        out = {}
        if p.exists():
            with gzip.open(p, 'rt') as f:
                for line in f:
                    r = json.loads(line)
                    if r.get('new_open_urls'):
                        out[r['key']] = r
        _CACHE[school] = out
    return _CACHE[school]


def APPLIES(school, paper):
    return paper.key in ledger(school)


def discover(school, papers, ctx):
    import re
    import ftp_common as F
    import s2_key_lookup as s2k
    import core_search as cs
    rec = ledger(school)
    arx, rows = {}, []
    memo = {}
    for p in papers:
        r = rec[p.key]
        src = ','.join(c['source'] for c in r.get('checks') or [] if c.get('result') == 'found')
        for u in r['new_open_urls']:
            if u.startswith('arXiv:'):
                arx.setdefault(p.work_id, re.sub(r'v\d+$', '', u[6:]))
            elif u.startswith('PMC'):
                for f in s2k.pmc_files(ctx.session(), re.sub(r'\D', '', u), memo):
                    rows.append(dict(work_id=p.work_id, url=f, landing_url=f'https://pmc.ncbi.nlm.nih.gov/articles/{u}/', version=None,
                                     source='ledger_found_pmc', detail=json.dumps(dict(checks=src, ledger_checked_at=r.get('checked_at')))))
            elif u.startswith('http') and s2k.ok_pdf(u) and cs.usable(u):
                rows.append(dict(work_id=p.work_id, url=u, landing_url=None, version=None, source='ledger_found',
                                 detail=json.dumps(dict(checks=src, ledger_checked_at=r.get('checked_at')))))
    brows, ctx.n['ledger_found_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'ledger_found_arxiv_bulk') if arx else ([], 0)
    by_w = {}
    for x in rows + brows:
        by_w.setdefault(x['work_id'], []).append(x)
    for p in papers:
        yield ctx.result(p, 'found' if by_w.get(p.work_id) else 'none', by_w.get(p.work_id, []),
                         query='open copies found by the unavailability ledger: ' + ', '.join(rec[p.key]['new_open_urls'][:3]))
