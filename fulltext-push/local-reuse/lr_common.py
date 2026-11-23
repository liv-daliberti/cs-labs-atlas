"""Shared state for the local-reuse harvest (2026-10-29): the lab papers without a copy at the six schools, and the PDFs
the six catalogs already hold.

missing   (snapshot) every lab paper of every school with no copy by the coverage counter's rule, with its catalog work
          (ftp_common.match_work; None when the catalog has no work for it), DOI, edition DOIs, title, year, byline, PIs
          -> missing.jsonl.gz
stores    (snapshot) every downloaded work of the six catalogs: school, work id, DOI, title, year, file path, sha256
          -> stores.jsonl.gz
Both are read read-only in short rowid chunks (ftp_common.chunks), as every reader of the catalogs does.
LR_SCHOOLS selects target school keys (space/comma separated, or all built schools).
LR_SOURCE_SCHOOLS selects source catalogs independently (or all initialized catalogs).
Both default to the original six schools. CS_ATLAS_FT_LOCAL_REUSE can isolate a run's inventory.
usage: lr_common.py snapshot | schools
"""
import gzip, json, os, re, sqlite3, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ftp_common as F

LEGACY_SCHOOLS = ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford')


def selected_schools(value, targets=False):
    """Explicit keys or all initialized catalogs; targets also need a built paper list."""
    if not value:
        return LEGACY_SCHOOLS
    if value.strip() == 'all':
        return tuple(sorted(p.name for p in F.FT.iterdir()
                            if (p / 'catalog.sqlite').is_file()
                            and (not targets or F.P.data('lab_papers.jsonl.gz', p.name).is_file())))
    keys = tuple(dict.fromkeys(value.replace(',', ' ').split()))
    if not keys or any(not re.fullmatch(r'[a-z][a-z0-9_-]*', k) for k in keys):
        raise ValueError('LR_SCHOOLS / LR_SOURCE_SCHOOLS must be school keys or all')
    return keys


SCHOOLS = selected_schools(os.environ.get('LR_SCHOOLS'), targets=True)
SOURCE_SCHOOLS = selected_schools(os.environ.get('LR_SOURCE_SCHOOLS') or os.environ.get('LR_SCHOOLS'))


def source_rows(db, wanted=None):
    """Read the slim metadata index first; fetch object paths only for possible matches."""
    if wanted is None:
        yield from F.chunks(db, 'works', 'id, doi, title, year, status, file_path, sha256')
        return
    dois, titles = wanted
    possible = []
    for i, d, t, y, st, sha in F.works_rows(db, 'id, doi, title, year, status, sha256'):
        if st == 'downloaded' and sha and (F.ndoi(d) in dois or F.nt(t) in titles):
            possible.append((i, d, t, y, st, sha))
    for start in range(0, len(possible), 200):
        part = possible[start:start + 200]
        paths = dict(F.read_retry(db, f'SELECT id,file_path FROM works WHERE id IN ({",".join("?" * len(part))})',
                                 [r[0] for r in part]))
        for i, d, t, y, st, sha in part:
            yield i, d, t, y, st, paths.get(i), sha


def family(name):
    """A byline name's family name, normalized (ASCII letters, lower case); '' when too short to be evidence."""
    toks = [t for t in re.split(r'[\s,]+', unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()) if t]
    toks = [re.sub(r'[^a-z]', '', t) for t in toks]
    toks = [t for t in toks if t and t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return toks[-1] if toks and len(toks[-1]) >= 3 else ''


def snapshot():
    F.P.FT_LOCAL_REUSE.mkdir(parents=True, exist_ok=True)
    with gzip.open(F.P.FT_LOCAL_REUSE / 'missing.jsonl.gz.part', 'wt') as f:
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
    (F.P.FT_LOCAL_REUSE / 'missing.jsonl.gz.part').replace(F.P.FT_LOCAL_REUSE / 'missing.jsonl.gz')
    wanted = None
    if os.environ.get('LR_SOURCES_MATCH_ONLY') == '1':
        missing = load_missing()
        wanted = ({F.ndoi(d) for r in missing for d in [r.get('doi')] + r.get('editions', []) if d},
                  {F.nt(r.get('title')) for r in missing if len(F.nt(r.get('title'))) >= 20})
    with gzip.open(F.P.FT_LOCAL_REUSE / 'stores.jsonl.gz.part', 'wt') as f:
        for school in SOURCE_SCHOOLS:
            db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
            n = 0
            for i, d, t, y, st, fp, sha in source_rows(db, wanted):
                if st == 'downloaded' and fp and sha:
                    f.write(json.dumps(dict(school=school, work_id=i, doi=F.ndoi(d) or None, title=t, year=y, file_path=fp, sha256=sha)) + '\n'); n += 1
            shas = set()
            for (sha,) in F.chunks(db, 'assets', 'sha256', n=20000):
                if sha:
                    shas.add(sha)
            db.close()
            f.write(json.dumps(dict(school=school, asset_shas=sorted(shas))) + '\n')
            print(json.dumps(dict(school=school, downloaded=n, asset_shas=len(shas))), flush=True)
    (F.P.FT_LOCAL_REUSE / 'stores.jsonl.gz.part').replace(F.P.FT_LOCAL_REUSE / 'stores.jsonl.gz')


def load_missing():
    return [json.loads(l) for l in gzip.open(F.P.FT_LOCAL_REUSE / 'missing.jsonl.gz', 'rt')]


def load_stores():
    works, shas = [], {}
    for l in gzip.open(F.P.FT_LOCAL_REUSE / 'stores.jsonl.gz', 'rt'):
        r = json.loads(l)
        if 'asset_shas' in r:
            for s in r['asset_shas']:
                shas.setdefault(s, set()).add(r['school'])
        else:
            works.append(r); shas.setdefault(r['sha256'], set()).add(r['school'])
    return works, shas


if __name__ == '__main__':
    {'snapshot': snapshot, 'schools': lambda: print(' '.join(SCHOOLS))}[sys.argv[1]]()
