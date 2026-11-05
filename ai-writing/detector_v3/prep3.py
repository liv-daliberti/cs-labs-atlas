"""Data for detector v3: every train-split pre-period human passage, and sources for the ten new generators.

human   data/human_train.jsonl.gz: every passage of every train-split 2016-2021 pool paper (v2's pool: usable full text),
        {key, school, year, kind, pidx, text}. The train script samples from it and mines hard negatives with v2's scores.
sources data/sources3.jsonl: per new generator and split, N sources by v2's rounds rule (one passage per paper per round,
        never the paper's first passage, 60-400 words, paper has a title), generator-specific shuffles so that generators
        see different passages; task cycles over six tasks and temperature over 0.3/0.7/1.0.
        train 3000 / cal 500 / test 1500 per generator.
usage: prep3.py --db <fulltext.sqlite> [-j 16]
"""
import argparse, gzip, json, random, re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import v3common as C
import prep as P2  # detector_v2/prep.py

V = C.V
QUOTA = dict(train=3000, cal=500, test=1500)
TEMPS = (0.3, 0.7, 1.0)
SENT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\[])')


def main(db, j):
    P2.KEEP = 60
    meta = P2.load_meta()
    import sqlite3
    d = sqlite3.connect(f'file:{db}?mode=ro&immutable=1', uri=True)
    hi = d.execute('select max(rowid) from texts').fetchone()[0]; d.close()
    recs = []
    with ProcessPoolExecutor(j, initializer=P2.init, initargs=(meta,)) as ex:
        for res in ex.map(P2.worker, [(db, lo, lo + 400) for lo in range(0, hi + 1, 400)]):
            recs += [r for r in res if 'cand' in r]
    pool = {r['key']: r for r in recs}
    print('pool papers', len(pool), flush=True)
    C.DATA.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(C.DATA / 'human_train.jsonl.gz', 'wt') as f:
        for k in sorted(pool):
            if V.split_of(k) != 'train':
                continue
            r = pool[k]
            for i, t in r['cand']:  # KEEP=60 shuffled candidates: all passages of all but the longest papers
                f.write(json.dumps(dict(key=k, school=r['school'], year=r['year'], kind=r['kind'], pidx=i, text=t), ensure_ascii=False) + '\n'); n += 1
    print('human train passages', n, flush=True)
    out, stats = [], Counter()
    for gi, gen in enumerate(C.V3GENS):
        for sp in ('train', 'cal', 'test'):
            keys = sorted(k for k in pool if V.split_of(k) == sp and meta[k][2])
            rng = random.Random(f'{C.SEED}|{gen}|{sp}')
            rng.shuffle(keys)
            lists = {}
            for k in keys:
                c = [(i, t) for i, t in pool[k]['cand'] if i > 0 and 60 <= len(t.split()) <= 400]
                random.Random(f'{C.SEED}|{gen}|{k}').shuffle(c)
                lists[k] = c
            picked = []
            for k, (i, t) in P2.rounds(keys, lists):
                if len(picked) >= QUOTA[sp]:
                    break
                picked.append((k, i, t))
            rng.shuffle(picked)
            off = rng.randrange(6)
            for m, (k, i, t) in enumerate(picked):
                task = C.TASKS3[(m + off) % 6]
                s = dict(sid=f'{gen}-{sp}-{m}', gen=gen, family=C.FAMILY[gen], split=sp, key=k, school=pool[k]['school'], year=pool[k]['year'],
                         title=meta[k][2], kind=pool[k]['kind'], pidx=i, text=t, task=task, temp=TEMPS[(m // 6 + gi) % 3])
                if task == 'partial':
                    ss = SENT.split(t)
                    if len(ss) < 3:
                        s['task'] = 'polish'
                    else:
                        nsel = max(1, round(len(ss) * rng.choice((0.3, 0.5, 0.7))))
                        s['sel'] = sorted(rng.sample(range(len(ss)), nsel))
                out.append(s); stats[f"{gen}/{sp}"] += 1
    with open(C.DATA / 'sources3.jsonl', 'w') as f:
        for s in out:
            f.write(json.dumps(s, ensure_ascii=False) + '\n')
    json.dump(dict(human_train=n, sources=len(out), by=stats, tasks=Counter(s['task'] for s in out)), open(C.DATA / 'prep3_stats.json', 'w'), indent=1)
    print(json.dumps(dict(sources=len(out), by=stats)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--db', default=str(V.FULLTEXT)); ap.add_argument('-j', type=int, default=16)
    a = ap.parse_args(); main(a.db, a.j)
