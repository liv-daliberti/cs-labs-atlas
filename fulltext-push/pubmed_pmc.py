"""pubmed_pmc: route PubMed landing-page candidates to their PMC open-data copies (2026-11-17).

Why: OpenAlex lists a work's PubMed record (https://pubmed.ncbi.nlm.nih.gov/<pmid>/) as a repository location. ftp_common.oa_location_rows
keeps a repository's landing page as a candidate, but a PubMed page has no PDF link, so the collector records 'Response has no unambiguous
primary PDF link' (2,958 PubMed URLs on 2026-11-16). PMC links in the same locations were routed to the PMC open-data bucket
(ftp_common.pmc_rows) and those PMC-id-bearing works were fine; a bare PubMed id never was, and the lab-paper pmc/europepmc channels
never look at the oa-expand batches.

What: per school, the works that are not local and have a PubMed landing candidate (and no PMC open-data candidate yet): PMID -> PMCID by the
NCBI PMC ID Converter (https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/, <= 200 ids per request, robots allow /tools/, Crawl-delay 1 s,
one request at a time), then the PDF / JATS XML of that PMCID in NLM's PMC open-data bucket (s2_key_lookup.pmc_files). Nothing is scraped from
pubmed or pmc pages; a PMCID outside the open-data subset yields no row. Identity stays with the collector's page-1 rule at download time.
Candidate rows use source 'pubmed_pmc_open_data', detail = '<pmid>:<pmcid>'.

DRY by default (read-only catalog scan). Writes go through the plan/apply pattern of queued_oa_fill.py (plan file, fresh school-named backup,
catalog write lock wait, INSERT OR IGNORE candidates only, integrity_check).
usage: pubmed_pmc.py plan <school>[,...] --out PLAN.json.gz [--limit N] [--statuses needs_access_review,queued]
       pubmed_pmc.py apply PLAN.json.gz <school>[,...] --backup-dir DIR [--lock-wait 2700]
"""
import argparse
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

PUBMED = re.compile(r'^https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?(?:[?#].*)?$', re.I)
IDCONV = 'https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/'
TOOL = 'homogenizing-science-pmc-routing'  # a tool name only; no contact address is sent
SOURCE = 'pubmed_pmc_open_data'
BATCH = 200
DELAY = 1.0  # robots Crawl-delay for pmc.ncbi.nlm.nih.gov


def pubmed_works(school, statuses=('needs_access_review', 'queued'), path=None):
    """[(work id, pmid, doi)]: works in `statuses` with a PubMed landing candidate and no PMC open-data candidate (read-only)."""
    path = path or F.FT / school / 'catalog.sqlite'
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=120)
    try:
        q = ','.join('?' * len(statuses))
        rows = db.execute(f"SELECT w.id, c.url, w.doi FROM works w JOIN candidates c ON c.work_id=w.id "
                          f"WHERE w.status IN ({q}) AND c.url LIKE '%pubmed.ncbi.nlm.nih.gov/%'", list(statuses)).fetchall()
        have = {r[0] for r in db.execute("SELECT DISTINCT work_id FROM candidates WHERE url LIKE '%pmc-oa-opendata%'")}
    finally:
        db.close()
    out = {}
    for w, url, doi in rows:
        m = PUBMED.match(url or '')
        if m and w not in have:
            out.setdefault(w, (w, m.group(1), doi))
    return sorted(out.values())


def parse_idconv(js):
    """{pmid: pmcid digits} from one idconv JSON answer (records without a pmcid are absent)."""
    out = {}
    for r in (js or {}).get('records') or []:
        if r.get('pmcid') and r.get('pmid') and r.get('status') != 'error':
            out[str(r['pmid'])] = re.sub(r'\D', '', r['pmcid'])
    return out


def idconv(session, pmids, cache, delay=DELAY):
    """Fill cache {pmid: pmcid digits | ''} for the pmids not in it: batches of 200, `delay` seconds apart. A failed request leaves the batch
    uncached (asked again next run); 429/5xx wait 60 s once, then stop (no workaround of a rate limit)."""
    todo = [p for p in dict.fromkeys(pmids) if p not in cache]
    last = 0.0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        time.sleep(max(0.0, delay - (time.monotonic() - last)))
        for attempt in range(2):
            last = time.monotonic()
            r = session.get(IDCONV, params=dict(ids=','.join(chunk), format='json', tool=TOOL, idtype='pmid'), timeout=(15, 60))
            if r.status_code == 200:
                break
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(60)
                continue
            raise RuntimeError(f'idconv HTTP {r.status_code}')
        found = parse_idconv(r.json())
        for p in chunk:
            cache[p] = found.get(p, '')
    return cache


def plan_rows(works, cache, session, memo=None):
    """-> (rows, Counter) for [(work, pmid, doi)] given the idconv cache; PMC open-data files by s2_key_lookup.pmc_files."""
    import collections
    import s2_key_lookup as s2k
    memo = {} if memo is None else memo
    n = collections.Counter(works=len(works))
    rows = []
    for w, pmid, _doi in works:
        pmc = cache.get(pmid)
        if not pmc:
            n['no_pmcid'] += 1
            continue
        n['pmcid'] += 1
        files = s2k.pmc_files(session, pmc, memo)
        if not files:
            n['not_in_open_data'] += 1
            continue
        n['works_with_files'] += 1
        for u in files:
            rows.append(dict(work_id=w, url=u, landing_url=f'https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc}/', version=None, license=None,
                             source=SOURCE, detail=f'{pmid}:PMC{pmc}'))
    n['rows'] = len(rows)
    return rows, n


def make_plan(schools, out, limit=None, statuses=('needs_access_review', 'queued'), cache_file=None):
    import requests
    s = requests.Session()
    s.headers['User-Agent'] = F.UA
    cache_file = Path(cache_file) if cache_file else None
    cache = {}
    if cache_file and cache_file.exists():
        cache = json.loads(cache_file.read_text())
    saved, memo = {}, {}
    per = {sc: pubmed_works(sc, statuses) for sc in schools}
    if limit:  # a deterministic spread over the schools, for a dry run
        per = {sc: v[:max(1, limit // len(schools))] for sc, v in per.items()}
    idconv(s, [p for v in per.values() for _w, p, _d in v], cache)
    if cache_file:
        cache_file.write_text(json.dumps(cache))
    for sc, works in per.items():
        rows, n = plan_rows(works, cache, s, memo)
        saved[sc] = dict(counts=dict(n), rows=rows)
        print(json.dumps(dict(at=F.now(), school=sc, step='pubmed_pmc_plan', **n)), flush=True)
    tmp = Path(str(out) + '.part')
    with gzip.open(tmp, 'wt') as f:
        json.dump(dict(made_at=F.now(), schools=saved), f)
    os.replace(tmp, out)
    return saved


def apply_plan(plan_file, schools, backup_dir, lock_wait=2700, ev_dir=None, check=None):
    """Per school: fresh backup (queued_oa_fill.check_backup), wait for the catalog write lock, INSERT OR IGNORE the planned rows whose work
    is still in a candidate-less-for-PMC non-local state, integrity_check. Works are not touched: the next collector pass asks the new
    candidate (a work at needs_access_review is requeued by retry_transient/requeue_causes, which also keeps its own log)."""
    import queued_oa_fill as Q
    check = check or Q.integrity_ok
    with gzip.open(plan_file, 'rt') as f:
        saved = json.load(f)['schools']
    for s in schools:
        Q.check_backup(s, backup_dir)
    done = {}
    for s in schools:
        Q.check_no_writer(s, lock_wait, 15)
        Q.check_backup(s, backup_dir)
        still = {w for w, _p, _d in pubmed_works(s)}
        rows = [r for r in saved.get(s, {}).get('rows', []) if r['work_id'] in still]
        import lab_channels as L
        ev = ev_dir or F.FT / s / 'discovery' / f'claude-{s}-pubmed-pmc' / 'evidence'
        added = L.write(s, rows, 'pubmed_pmc', ev_dir=ev) if rows else 0
        done[s] = dict(planned=len(saved.get(s, {}).get('rows', [])), still_wanted=len(rows), written=added, integrity=bool(check(s)))
        print(json.dumps(dict(at=F.now(), school=s, step='pubmed_pmc_apply', **done[s])), flush=True)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan')
    p.add_argument('schools')
    p.add_argument('--out', required=True)
    p.add_argument('--limit', type=int)
    p.add_argument('--statuses', default='needs_access_review,queued')
    p.add_argument('--cache')
    a = sub.add_parser('apply')
    a.add_argument('plan')
    a.add_argument('schools')
    a.add_argument('--backup-dir', required=True)
    a.add_argument('--lock-wait', type=int, default=2700)
    x = ap.parse_args(argv)
    if x.cmd == 'plan':
        make_plan(x.schools.split(','), x.out, x.limit, tuple(x.statuses.split(',')), x.cache)
    else:
        apply_plan(x.plan, x.schools.split(','), x.backup_dir, x.lock_wait)


if __name__ == '__main__':
    main()
