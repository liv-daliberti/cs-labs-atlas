"""How many CS lab papers have a local copy (a downloaded PDF or full-text XML in the school's full-text catalog).

The catalogs (homogenizing-science/data/fulltext/<school>/catalog.sqlite) are written by running collectors over NFS
with a rollback journal: they are read in short rowid chunks, read-only (as claude-princeton-20261015's
catalog_snapshot does), never with one long SELECT. A lab paper matches a catalog work by collection work id, else <school>_oa_<OpenAlex W id> (lab papers the
fulltext-push added to a catalog), else DOI
(including arXiv's 10.48550 DOI from the work's arXiv id).
A work the collector left at needs_access_review carries the cause the stores' access review recorded
(fulltext-push/review_access.py -> catalog side table access_review(work_id, verdict, cause, causes_json, ...); 2026-10-29):
access_cause (the deciding cause: paywall_or_forbidden, login, challenge, robots_disallow, landing_no_pdf, not_found, ...),
access_causes (every cause seen) and access_verdict ('closed', or a requeue verdict). The table is read like the works
table: read-only, short rowid chunks, busy timeout.
-> hierarchy/<school>/copies.json {summary, papers: {paper key: {status, catalog, doi, oa, year, access_cause?, ...}}}
usage: lab_paper_copies.py <school> ...
"""
import collections, gzip, json, re, sqlite3, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; FT = P.STORES
LOCAL = ('downloaded', 'fulltext_xml')


def chunks(db, sql_cols, chunk=1500):
    hi = db.execute('select max(rowid) from works').fetchone()[0] or 0
    for lo in range(0, hi + 1, chunk):
        yield from db.execute(f'select {sql_cols} from works where rowid >= ? and rowid < ?', (lo, lo + chunk)).fetchall()
        time.sleep(0.05)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def run(school):
    rows = [json.loads(l) for l in gzip.open(HERE / 'hierarchy' / school / 'lab_papers.jsonl.gz', 'rt')]
    status, by_doi, local_titles, access = {}, {}, set(), {}  # the coverage counter's rule: any catalog work with the same id, DOI or title
    if (FT / school / 'catalog.sqlite').exists():
        db = sqlite3.connect(f'file:{FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
        db.execute('pragma busy_timeout = 120000')
        if db.execute("select 1 from sqlite_master where type='table' and name='access_review'").fetchone():
            hi = db.execute('select max(rowid) from access_review').fetchone()[0] or 0
            for lo in range(0, hi + 1, 1500):
                for wid, verdict, cause, causes in db.execute('select work_id, verdict, cause, causes_json from access_review where rowid >= ? and rowid < ?', (lo, lo + 1500)).fetchall():
                    try:
                        causes = json.loads(causes) if causes else None
                    except ValueError:
                        pass
                    access[wid] = dict(access_verdict=verdict, access_cause=cause, access_causes=causes)
                time.sleep(0.05)
        for wid, doi, st, title in chunks(db, 'id, doi, status, title'):
            if status.get(wid) not in LOCAL:
                status[wid] = st
            if doi and (st in LOCAL or ndoi(doi) not in by_doi):
                by_doi[ndoi(doi)] = wid
            if st in LOCAL and title:
                local_titles.add(re.sub(r'[^a-z0-9]', '', title.lower()))
    out, n = {}, collections.Counter()
    for r in rows:
        key = r['work'] or r['oa']
        if key in out:
            continue
        st, cid = None, None
        for e in [r] + list(r.get('editions') or []):  # one unique paper: a copy of any edition counts
            oaw = f"{school}_oa_{(e.get('oa') or '').rsplit('/', 1)[-1]}"  # lab papers added to a catalog under their OpenAlex id (fulltext-push, 2026-10-22)
            c_ = e.get('work') if e.get('work') in status else (oaw if oaw in status else None) or by_doi.get(ndoi(e.get('doi'))) or (by_doi.get('10.48550/arxiv.' + r['arxiv']) if r.get('arxiv') else None)
            if c_ and (cid is None or status.get(c_) in LOCAL):
                cid = c_
            if cid and status.get(cid) in LOCAL:
                break
        st = status.get(cid) if cid else None
        if st not in LOCAL and re.sub(r'[^a-z0-9]', '', (r.get('title') or '').lower()) in local_titles:
            st = 'downloaded'  # another catalog record of the same paper (same title) has the copy
        out[key] = dict(status=st or 'not_in_catalog', catalog=cid, doi=r.get('doi'), oa=r['oa'], year=r.get('year'))
        if st == 'needs_access_review':
            out[key].update(access.get(cid) or dict(access_cause=None))
            n['access_cause:' + str(out[key].get('access_cause'))] += 1
        n['local' if st in LOCAL else (st or 'not_in_catalog')] += 1
    summary = dict(school=school, lab_papers=len(out), **n, local_share=round(n['local'] / max(1, len(out)), 3))
    json.dump(dict(summary=summary, papers=out), open(HERE / 'hierarchy' / school / 'copies.json', 'w'))
    print(json.dumps(summary))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
