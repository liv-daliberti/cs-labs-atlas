"""A school's OpenAlex institution sweep from the local snapshot instead of the API (docs/OPENALEX-SNAPSHOT.md section 9, first code path).

Writes hierarchy/<key>/openalex-sweep.sqlite in the layout tools/oa_sweep.py writes (table pages: year, page, cursor, next_cursor, n, count, fetched_at,
body = zlib JSON list of works with the sweep's SELECT fields), so the readers (sweep_check, cs_related_candidates, the builder) need no change. Same
filter as the API sweep: an authorship institution whose lineage holds one of the charter's sweep ids (lineage + related), at most 100 authorships,
publication years from the charter window. Uses `works_by_lineage` over the main snapshot store and its extensions (ext-<key>.sqlite).
`meta` (table) records the source: snapshot date, extension files, the ids, the counts. No API credit is spent; the API stays the freshness layer for
works newer than the snapshot (rerun `atlas sweep <key>` after the daily reset only for the current year, if needed).

usage: sweep_from_snapshot.py <key> [--replace]      (refuses to overwrite an existing sweep file unless --replace; then the file is rebuilt)
"""
import argparse, json, sqlite3, sys, time, zlib

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import oa_snapshot as O  # noqa: E402

SELECT = ('id', 'doi', 'title', 'publication_year', 'publication_date', 'type', 'authorships', 'ids', 'primary_location')
PAGE = 200


def project(w):
    return {k: w.get(k) for k in SELECT if k in w}


def works_of_year(ids, year, root=None):
    """Distinct works of the snapshot with an authorship at one of the lineage ids in `year` and at most 100 authors, in id order."""
    seen = {}
    for i in ids:
        for w in O.works_by_lineage(i, year, root=root):
            if len(w.get('authorships') or []) <= 100:
                seen.setdefault(w['id'], w)
    return [seen[k] for k in sorted(seen)]


def build(key, out, root=None, years=None):
    cfg = S.get(key)
    lo, hi = cfg.get('window') or (2016, 2026)
    ids = S.sweep_ids(key)
    out = sqlite3.connect(str(out))
    out.execute('create table if not exists pages (year int, page int, cursor text, next_cursor text, n int, count int, fetched_at text, body blob, primary key (year, page))')
    out.execute('create table if not exists meta (key text primary key, value text)')
    d = O.snapshot_date(root)
    counts = {}
    for y in years or range(lo, hi + 1):
        ws = works_of_year(ids, y, root)
        counts[y] = len(ws)
        out.execute('delete from pages where year=?', (y,))
        for p in range(0, max(1, (len(ws) + PAGE - 1) // PAGE)):
            chunk = [project(w) for w in ws[p * PAGE:(p + 1) * PAGE]]
            out.execute('insert into pages values (?,?,?,?,?,?,?,?)', (y, p, f'snapshot:{d}', None, len(chunk), len(ws), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                                        zlib.compress(json.dumps(chunk, ensure_ascii=False).encode(), 6)))
        out.commit()
        print(json.dumps({'school': key, 'year': y, 'works': len(ws), 'count': len(ws), 'source': f'openalex_snapshot:{d}'}), flush=True)
    out.execute('insert or replace into meta values (?,?)', ('source', json.dumps(dict(snapshot_date=d, ids=ids, years=counts, built_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                                                     extensions=[str(p) for p in sorted((P.OA_SNAPSHOT / d).glob('ext-*.sqlite'))] if root is None else []))))
    out.commit(); out.close()
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('--replace', action='store_true')
    a = ap.parse_args(argv)
    dest = P.data_w('openalex-sweep.sqlite', a.key)
    if dest.exists() and not a.replace:
        sys.exit(f'{dest} exists (an API sweep may be resumable: atlas sweep {a.key}); pass --replace to rebuild it from the snapshot')
    if dest.exists():
        dest.unlink()
    build(a.key, dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
