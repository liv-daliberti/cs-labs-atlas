"""One entry per paper in the stores (ROADMAP #28): DOI sibling works collapse onto one canonical work through an ALIAS table.

Two ingest paths put the same paper into a store catalog twice (berkeley_oa_W... from the OpenAlex lab-paper discovery and
berkeley_<hash> from the catalog discovery, both with the same DOI). Nothing is deleted and no file moves: `work_alias` maps each
sibling to its canonical work, the view `work_canonical` gives every work its canonical id, and readers (lab_paper_copies, the identity
review, the reader export) count and check CANONICAL works (`resolve`). objects/ stays content-addressed. The alias can only merge.

  work_alias(alias_id PRIMARY KEY, canonical_id, basis, key, decided_at)   basis is 'doi' (the only basis ever applied)
  work_canonical(id, canonical_id)                                         view over works LEFT JOIN work_alias

Canonical choice (deterministic, `choose_canonical`): a work with a downloaded copy first, then one whose identity check passed, then the
one with a file, then the smallest id. So a group that has a downloaded copy always has a downloaded canonical (coverage cannot drop).
A DOI group joins only works whose titles overlap by at least 0.5 of the shorter title's words; the others are reported as doi_title_conflict.
Title + year groups are a REVIEW REPORT only (they are often a preprint and its published version): never applied.

  catalog_alias.py [school ...]            dry run (read-only): groups, canonical choice, coverage before/after, 10 sample groups per school
  catalog_alias.py [school ...] --apply    backup_catalog(store, 'before-alias'), then the rows in short transactions of at most 200 under the
                                           catalog write lock (fulltext-push/catalog_lock.py)
  --report FILE                            write the dry-run report as JSON
"""
import argparse, datetime, json, re, sqlite3, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import atlas_paths as P  # noqa: E402
import reader_links as RL  # noqa: E402

BATCH = 200
MIN_TITLE_OVERLAP = 0.5
SCHEMA = """
CREATE TABLE IF NOT EXISTS work_alias (
  alias_id TEXT PRIMARY KEY,
  canonical_id TEXT NOT NULL,
  basis TEXT NOT NULL CHECK (basis IN ('doi')),
  key TEXT NOT NULL,
  decided_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS work_alias_canonical ON work_alias(canonical_id);
CREATE VIEW IF NOT EXISTS work_canonical AS
  SELECT w.id AS id, COALESCE(a.canonical_id, w.id) AS canonical_id FROM works w LEFT JOIN work_alias a ON a.alias_id = w.id;
"""


def norm_doi(d):
    d = (d or '').strip().lower()
    d = re.sub(r'^(?:https?://)?(?:dx\.)?doi\.org/', '', d)
    return re.sub(r'^doi:', '', d).strip() or None


def title_key(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


def rank(w):
    """Sort key of a candidate canonical work (smaller is better): downloaded, identity-checked, with a file, then id."""
    return (w['status'] != 'downloaded', not w['identity_check'], not w['file_path'], w['id'])


def choose_canonical(works):
    return min(works, key=rank)['id']


def load(conn):
    cols = 'id, title, doi, year, status, file_path, identity_check'
    return [dict(zip(('id', 'title', 'doi', 'year', 'status', 'file_path', 'identity_check'), r)) for r in conn.execute(f'select {cols} from works')]


def plan(works):
    """{doi groups: [(key, canonical, [aliases])], conflicts: [key], title_year: [[ids]], stats}. Pure: no database."""
    by = {}
    for w in works:
        k = norm_doi(w['doi'])
        if k:
            by.setdefault(k, []).append(w)
    groups, conflicts, lost = [], [], 0
    for k in sorted(by):
        ws = by[k]
        if len(ws) < 2:
            continue
        canon = choose_canonical(ws)
        cw = next(w for w in ws if w['id'] == canon)
        ok = [w for w in ws if w is cw or RL.title_overlap(cw['title'], w['title']) >= MIN_TITLE_OVERLAP]
        if len(ok) < len(ws):
            conflicts.append(k)
        if len(ok) < 2:
            continue
        al = sorted(w['id'] for w in ok if w['id'] != canon)
        # the invariant: a group with a downloaded copy has a downloaded canonical
        if any(w['status'] == 'downloaded' for w in ok) and cw['status'] != 'downloaded':
            lost += 1
        groups.append((k, canon, al))
    ty = {}
    for w in works:
        t = title_key(w['title'])
        if len(t) > 20:
            ty.setdefault((t, w['year']), []).append(w['id'])
    title_year = [sorted(v) for v in ty.values() if len(v) > 1]
    dl = sum(1 for w in works if w['status'] == 'downloaded')
    aliased = {a for g in groups for a in g[2]}
    canon_dl = sum(1 for w in works if w['status'] == 'downloaded' and w['id'] not in aliased)
    stats = dict(works=len(works), doi_groups=len(groups), aliases=len(aliased), canonical_works=len(works) - len(aliased),
                 doi_title_conflicts=len(conflicts), downloaded_before=dl, canonical_downloaded_after=canon_dl,
                 groups_whose_canonical_lost_a_download=lost, title_year_groups_for_review=len(title_year),
                 title_year_extra_works=sum(len(v) - 1 for v in title_year))
    return dict(groups=groups, conflicts=conflicts, title_year=title_year, stats=stats)


def resolve(conn):
    """{alias_id: canonical_id} of a catalog connection ({} when it has no work_alias table). What readers use to count canonical works."""
    try:
        return dict(conn.execute('select alias_id, canonical_id from work_alias'))
    except sqlite3.OperationalError:
        return {}


def canonical_of(conn_or_map, work_id):
    m = conn_or_map if isinstance(conn_or_map, dict) else resolve(conn_or_map)
    return m.get(work_id, work_id)


def apply(store, groups, now=None):
    """Write the alias rows for a store: a locked backup first, then batches of at most BATCH rows, each its own short transaction."""
    sys.path.insert(0, str(P.FULLTEXT_PUSH))
    import catalog_lock as CL
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with CL.catalog_lock(store):
        pass
    CL.backup_catalog(store, 'before-alias')
    rows = [(a, canon, 'doi', k, now) for k, canon, al in groups for a in al]
    n = 0
    for i in range(0, len(rows), BATCH):
        with CL.catalog_lock(store):
            db = sqlite3.connect(str(Path(store) / 'catalog.sqlite'), timeout=60)
            try:
                db.executescript(SCHEMA)
                db.executemany('insert or ignore into work_alias values (?,?,?,?,?)', rows[i:i + BATCH])
                db.commit()
                n += db.total_changes
            finally:
                db.close()
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report')
    a = ap.parse_args(argv)
    out = {}
    for s in a.schools or P.SCHOOL_IDS:
        store = P.store(s)
        conn = sqlite3.connect(f'file:{store}/catalog.sqlite?mode=ro', uri=True)
        pl = plan(load(conn))
        conn.close()
        st = pl['stats']
        print(s, json.dumps(st))
        out[s] = dict(stats=st, sample=[dict(doi=k, canonical=c, aliases=al) for k, c, al in pl['groups'][:10]], conflicts=pl['conflicts'][:10],
                      title_year_sample=pl['title_year'][:10])
        if a.apply:
            if st['groups_whose_canonical_lost_a_download']:
                raise SystemExit(f'{s}: refused, a canonical lost a download')
            print(f'  applied {apply(store, pl["groups"])} alias rows')
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
