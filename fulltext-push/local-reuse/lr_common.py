"""Shared state for the local-reuse harvest (2026-10-29): the lab papers without a copy at the six schools, and the PDFs
the six catalogs already hold.

missing   (snapshot) every lab paper of every school with no copy by the coverage counter's rule, with its catalog work
          (ftp_common.match_work; None when the catalog has no work for it), DOI, edition DOIs, title, year, byline, PIs
          -> missing.jsonl.gz
stores    (snapshot) every downloaded work of the six catalogs: school, work id, DOI, title, year, file path, sha256
          -> stores.jsonl.gz
Both are read read-only in short rowid chunks (ftp_common.chunks), as every reader of the catalogs does.
usage: lr_common.py snapshot
"""
import gzip, json, re, sqlite3, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ftp_common as F

SCHOOLS = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')


def family(name):
    """A byline name's family name, normalized (ASCII letters, lower case); '' when too short to be evidence."""
    toks = [t for t in re.split(r'[\s,]+', unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()) if t]
    toks = [re.sub(r'[^a-z]', '', t) for t in toks]
    toks = [t for t in toks if t and t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return toks[-1] if toks and len(toks[-1]) >= 3 else ''


def snapshot():
    with gzip.open(HERE / 'missing.jsonl.gz.part', 'wt') as f:
        for school in SCHOOLS:
            papers = F.lab_papers(school)
            cs = F.catalog_state(school, with_urls=False)
            n = 0
            for k, r in papers.items():
                if F.is_local(school, r, cs):
                    continue
                w = F.match_work(school, r, cs)
                eds = sorted({F.ndoi(e.get('doi')) for e in r.get('editions') or [] if e.get('doi')} - {F.ndoi(r.get('doi'))})
                f.write(json.dumps(dict(school=school, key=k, work_id=w, status=cs['status'].get(w), oa=r.get('oa'), doi=F.ndoi(r.get('doi')) or None,
                                        editions=eds, title=r.get('title'), year=r.get('year'), byline=r.get('byline') or [], pis=r.get('pis') or [])) + '\n')
                n += 1
            print(json.dumps(dict(school=school, lab_papers=len(papers), missing=n)), flush=True)
    (HERE / 'missing.jsonl.gz.part').replace(HERE / 'missing.jsonl.gz')
    with gzip.open(HERE / 'stores.jsonl.gz.part', 'wt') as f:
        for school in SCHOOLS:
            db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
            n = 0
            for i, d, t, y, st, fp, sha in F.chunks(db, 'works', 'id, doi, title, year, status, file_path, sha256'):
                if st == 'downloaded' and fp and sha:
                    f.write(json.dumps(dict(school=school, work_id=i, doi=F.ndoi(d) or None, title=t, year=y, file_path=fp, sha256=sha)) + '\n'); n += 1
            shas = set()
            for (sha,) in F.chunks(db, 'assets', 'sha256', n=20000):
                if sha:
                    shas.add(sha)
            db.close()
            f.write(json.dumps(dict(school=school, asset_shas=sorted(shas))) + '\n')
            print(json.dumps(dict(school=school, downloaded=n, asset_shas=len(shas))), flush=True)
    (HERE / 'stores.jsonl.gz.part').replace(HERE / 'stores.jsonl.gz')


def load_missing():
    return [json.loads(l) for l in gzip.open(HERE / 'missing.jsonl.gz', 'rt')]


def load_stores():
    works, shas = [], {}
    for l in gzip.open(HERE / 'stores.jsonl.gz', 'rt'):
        r = json.loads(l)
        if 'asset_shas' in r:
            for s in r['asset_shas']:
                shas.setdefault(s, set()).add(r['school'])
        else:
            works.append(r); shas.setdefault(r['sha256'], set()).add(r['school'])
    return works, shas


if __name__ == '__main__':
    {'snapshot': snapshot}[sys.argv[1]]()
