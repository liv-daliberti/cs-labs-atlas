"""Equal-results proof for the OpenAlex snapshot against the API sweeps (ROADMAP #24; docs/OPENALEX-SNAPSHOT.md section 10).

counts            per school and year 2016-2026: works in hierarchy/<school>/raw/openalex-sweep.sqlite (the API, lineage filter of
                  the charter's sweep ids, authors_count < 101, ENCODE dataset records dropped) against the snapshot's works under
                  the same ids, authors <= 100 and ENCODE drop; prints a table and the ratio snapshot/API
fields <school>   a sample of N works (default 1000) present in both: every projected field the sweeps read is compared
usage: oa_snapshot_compare.py counts [--schools a,b] | fields <school> [--n 1000]
"""
import argparse, json, random, sqlite3, zlib
from collections import Counter, defaultdict

import atlas_paths as P  # noqa: E402
import oa_snapshot as S  # noqa: E402
import school_config as SC  # noqa: E402

YEARS = range(2016, 2027)
ENCODE = 'https://doi.org/10.17989'


def api_works(school):
    """{work id: work dict} from the school's API sweep pages (all pages, deduplicated)."""
    c = sqlite3.connect(f'file:{P.data("openalex-sweep.sqlite", school)}?mode=ro', uri=True, timeout=60)
    out = {}
    for (b,) in c.execute('select body from pages'):
        for w in json.loads(zlib.decompress(b)):
            out[w['id']] = w
    return out


def api_counts(school):
    n, enc = Counter(), 0
    for w in api_works(school).values():
        if (w.get('doi') or '').startswith(ENCODE) and w.get('type') == 'dataset':
            enc += 1
            continue
        if len(w.get('authorships') or []) > 100:
            continue
        n[w.get('publication_year')] += 1
    return n, enc


def snapshot_counts(school):
    db, d = S.conn()
    ids = SC.sweep_ids(school)
    q = ','.join('?' * len(ids))
    n = Counter()
    for y, body in db.execute(f'select distinct w.year, w.id from works w join work_inst i on i.work_id=w.id where i.inst in ({q}) and w.year between 2016 and 2026', ids):
        n[y] += 1
    # authors <= 100: re-count with the authorship count for the long tail only
    big = Counter()
    for y, wid, b in db.execute(f'select w.year, w.id, w.body from works w where w.id in (select work_id from work_inst where inst in ({q})) and w.year between 2016 and 2026', ids):
        if len(S.unpack(b).get('authorships') or []) > 100:
            big[y] += 1
    return Counter({y: n[y] - big[y] for y in n}), d


def cmd_counts(schools):
    rows, lines = [], []
    lines.append(f'{"school":10} {"year":>5} {"API":>8} {"snapshot":>9} {"ratio":>7}')
    for s in schools:
        a, enc = api_counts(s)
        b, d = snapshot_counts(s)
        ta = tb = 0
        for y in YEARS:
            ta += a[y]; tb += b[y]
            lines.append(f'{s:10} {y:>5} {a[y]:>8} {b[y]:>9} {(b[y] / a[y] if a[y] else float("nan")):>7.3f}')
            rows.append(dict(school=s, year=y, api=a[y], snapshot=b[y]))
        lines.append(f'{s:10} {"all":>5} {ta:>8} {tb:>9} {(tb / ta if ta else float("nan")):>7.3f}   (API ENCODE records dropped: {enc}; snapshot {d})')
    print('\n'.join(lines))
    return rows


def norm(w):
    ships = w.get('authorships') or []
    pl = w.get('primary_location') or {}
    src = pl.get('source') or {}
    ids = w.get('ids') or {}
    return dict(doi=(w.get('doi') or '').lower() or None, title=w.get('title'), year=w.get('publication_year'), date=w.get('publication_date'),
                type=w.get('type'), authors=sorted((a.get('author') or {}).get('id') or '' for a in ships),
                insts=sorted({i.get('id') for a in ships for i in (a.get('institutions') or [])}),
                pmid=ids.get('pmid'), source=src.get('id'), landing=pl.get('landing_page_url'), pdf=pl.get('pdf_url'),
                license=pl.get('license'), version=pl.get('version'), is_oa=pl.get('is_oa'))


def cmd_fields(school, n):
    api = api_works(school)
    random.seed(1)
    keys = sorted(api)
    random.shuffle(keys)
    diff, seen, missing = Counter(), 0, 0
    examples = defaultdict(list)
    for k in keys:
        if seen >= n:
            break
        w = S.work(k)
        if w is None:
            missing += 1
            continue
        seen += 1
        a, b = norm(api[k]), norm(w)
        for f in a:
            if a[f] != b[f]:
                diff[f] += 1
                if len(examples[f]) < 3:
                    examples[f].append((k, a[f] if f not in ('authors', 'insts') else len(a[f]), b[f] if f not in ('authors', 'insts') else len(b[f])))
    print(json.dumps(dict(school=school, compared=seen, absent_from_snapshot=missing, differing_fields=dict(diff), examples=dict(examples), snapshot=S.snapshot_date()), indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('counts'); c.add_argument('--schools')
    f = sub.add_parser('fields'); f.add_argument('school'); f.add_argument('--n', type=int, default=1000)
    a = ap.parse_args()
    if a.cmd == 'counts':
        cmd_counts(a.schools.split(',') if a.schools else SC.keys())
    else:
        cmd_fields(a.school, a.n)


if __name__ == '__main__':
    main()
