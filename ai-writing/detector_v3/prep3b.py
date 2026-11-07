"""Held-out real text for v3: every passage of every cal-split and test-split 2016-2021 pool paper of the CURRENT full-text
store (data/cal_real3.jsonl.gz, data/test_real3.jsonl.gz). The store has grown since v2 (more schools and papers), so these
sets are larger than v2's (59,838 / 114,050 passages); the v2 sets are a subset by key. Split rule unchanged (sha1 of the key).
usage: prep3b.py --db <fulltext.sqlite> [-j 16]
"""
import argparse, gzip, json
from concurrent.futures import ProcessPoolExecutor
import v3common as C
import prep as P2

V = C.V


def main(db, j):
    P2.KEEP = 1
    meta = P2.load_meta()
    import sqlite3
    d = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
    hi = d.execute('select max(rowid) from texts').fetchone()[0]; d.close()
    fs = {p: gzip.open(C.DATA / f'{p}_real3.jsonl.gz', 'wt') for p in ('cal', 'test')}
    n = {p: 0 for p in fs}
    with ProcessPoolExecutor(j, initializer=P2.init, initargs=(meta,)) as ex:
        for res in ex.map(P2.worker, [(db, lo, lo + 400) for lo in range(0, hi + 1, 400)]):
            for r in res:
                if 'all' in r:
                    p = V.split_of(r['key'])
                    for i, t in enumerate(r['all']):
                        fs[p].write(json.dumps(dict(key=r['key'], school=r['school'], year=r['year'], kind=r['kind'], pidx=i, text=t), ensure_ascii=False) + '\n'); n[p] += 1
    for f in fs.values():
        f.close()
    print(json.dumps(n))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--db', default=str(V.FULLTEXT)); ap.add_argument('-j', type=int, default=16)
    a = ap.parse_args(); main(a.db, a.j)
