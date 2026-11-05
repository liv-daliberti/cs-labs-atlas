"""Pilot of fulltext_sections.py: seeded stratified sample, split, compare with today's body, outline for review.
usage: pilot.py sample SEED N OUT.json [--exclude PREV.json] [--db ft.sqlite]
       pilot.py run SAMPLE.json OUTDIR [-j 6]      (pdftotext cached as OUTDIR/txt/<i>.txt, results OUTDIR/res.jsonl)
"""
import argparse, gzip, json, random, sqlite3, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402
import fulltext_sections as S  # noqa: E402


def bucket(y):
    return 'pre2016' if y < 2016 else '2016-18' if y < 2019 else '2019-21' if y < 2022 else '2022-25'


def sample(seed, n, out, exclude, db):
    meta = {}
    for l in gzip.open(P.AI_WRITING / 'papers.jsonl.gz', 'rt'):
        p = json.loads(l)
        try:
            y = int(p['year'])
        except (TypeError, ValueError):
            continue
        if y <= 2025:
            meta[p['key']] = (y, p.get('venue'), p.get('type'), p.get('title'))
    skip = {r['key'] for r in json.load(open(exclude))} if exclude else set()
    c = sqlite3.connect(db)
    groups = defaultdict(list)
    for k, school, path, kind in c.execute('select key, school, path, kind from texts'):
        if k in meta and k not in skip:
            groups[(school, kind, bucket(meta[k][0]))].append(k)
    rnd = random.Random(seed)
    for g in groups.values():
        rnd.shuffle(g)
    # xml gets ~12% of the draw; the rest is spread round-robin over school x year bucket
    order = {'xml': [g for g in sorted(groups) if g[1] == 'xml'], 'pdf': [g for g in sorted(groups) if g[1] == 'pdf']}
    picked = []
    for kind, share in (('xml', max(1, round(n * 0.12))), ('pdf', None)):
        want = share if share else n - len(picked)
        gl = order[kind][:]; rnd.shuffle(gl)
        while want > 0 and any(groups[g] for g in gl):
            for g in gl:
                while groups[g] and want > 0:
                    k = groups[g].pop()
                    if (P.STORES / c.execute('select path from texts where key=?', (k,)).fetchone()[0]).exists():
                        picked.append(k); want -= 1
                    break
    rows = []
    for k in picked:
        school, path, kind = c.execute('select school, path, kind from texts where key=?', (k,)).fetchone()
        y, v, t, title = meta[k]
        rows.append(dict(key=k, school=school, path=path, kind=kind, year=y, venue=v, type=t, title=title))
    json.dump(rows, open(out, 'w'), indent=0)
    print(len(rows), {kk: sum(r['kind'] == kk for r in rows) for kk in ('pdf', 'xml')})


def one(job):
    i, r, outdir = job
    p = P.STORES / r['path']
    res = S.split_file(p, r['kind'])
    if 'error' in res:
        return dict(i=i, key=r['key'], error=res['error'])
    return dict(i=i, key=r['key'], flags=res['flags'], main=res['main'], references=res['references'], appendix=res['appendix'])


def run(sample_json, outdir, j):
    rows = json.load(open(sample_json)); outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(j) as ex, open(outdir / 'res.jsonl', 'w') as f:
        for r in ex.map(one, [(i, r, outdir) for i, r in enumerate(rows)], chunksize=2):
            f.write(json.dumps(r) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('a'); ap.add_argument('b', nargs='?'); ap.add_argument('c', nargs='?')
    ap.add_argument('--exclude'); ap.add_argument('--db', default='/tmp/od2961-sections/ft.sqlite'); ap.add_argument('-j', type=int, default=6)
    a = ap.parse_args()
    if a.cmd == 'sample':
        sample(int(a.a), int(a.b), a.c, a.exclude, a.db)
    else:
        run(a.a, a.b, a.j)
