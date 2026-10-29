"""Human passages and generation sources for the passage-level detector (v2).

pool     lab papers of ai-writing/papers.jsonl.gz published 2016-2021 whose full text (ai-writing/fulltext.sqlite) is
         usable (v2common.usable_text), cut into passages by the diversity battery's splitter.
split    by paper (v2common.split_of): train 70 / cal 10 / test 20.
sources  N_SRC passages to rewrite: one per paper per round (papers in random order, round r takes each paper's r-th
         shuffled passage), quotas per school proportional to the school's pool papers; a source is not the paper's
         first passage (title page / front matter), has 60-400 words, and its paper has a title. Shuffled, then
         source i goes to generator GENS[i % 3] and task TASKS[(i // 3) % 3]: 6,000 per generator, 2,000 per task.
humans   N_HUM further passages by the same rounds, disjoint from the sources (the sources' own passages are human
         examples too).
real     every passage of every cal-split pool paper (the 1%-FPR threshold) and of every test-split pool paper (the
         real-text false-positive check).
census   passage counts of every stored full text (all years), for sizing the scoring jobs.
-> data/sources.jsonl, data/humans.jsonl, data/cal_real.jsonl.gz, data/test_real.jsonl.gz, data/prep_stats.json
usage: prep.py --db <local copy of fulltext.sqlite> [-j 8]
"""
import argparse, gzip, json, random, sqlite3, zlib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import v2common as V

N_SRC, N_HUM, KEEP = 18000, 25000, 16


def load_meta():
    meta = {}
    for line in gzip.open(V.AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        try:
            y = int(p.get('year'))
        except (TypeError, ValueError):
            y = None
        meta[p['key']] = (p['school'], y, (p.get('title') or '').strip())
    return meta


META = {}


def init(meta):
    META.update(meta)


def worker(args):
    db_path, lo, hi = args
    meta = META
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    out = []
    for key, school, kind, body, flags in db.execute('select key, school, kind, body, flags from texts where rowid >= ? and rowid < ?', (lo, hi)):
        if not body:
            continue
        body = zlib.decompress(body).decode('utf-8', 'ignore')
        usable = V.usable_text(kind, body, json.loads(flags or '{}'))
        ps = V.passages(body)
        m = meta.get(key)
        year = m[1] if m else None
        rec = dict(key=key, school=school, kind=kind, year=year, usable=usable, n=len(ps), words=sum(len(p.split()) for p in ps))
        if m and usable and year in V.PRE and ps:
            rng = random.Random(f'{V.SEED}|{key}')
            idx = list(range(len(ps))); rng.shuffle(idx)
            rec['cand'] = [(i, ps[i]) for i in idx[:KEEP]]
            if V.split_of(key) in ('test', 'cal'):
                rec['all'] = ps
        out.append(rec)
    db.close()
    return out


def rounds(order, lists):
    """Yield items round by round: the r-th item of every list, lists taken in `order`."""
    r = 0
    while True:
        any_ = False
        for k in order:
            if r < len(lists[k]):
                any_ = True
                yield k, lists[k][r]
        if not any_:
            return
        r += 1


def main(db_path, j):
    meta = load_meta()
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    hi = db.execute('select max(rowid) from texts').fetchone()[0]; db.close()
    step = 400
    recs = []
    with ProcessPoolExecutor(j, initializer=init, initargs=(meta,)) as ex:
        for res in ex.map(worker, [(db_path, lo, lo + step) for lo in range(0, hi + 1, step)]):
            recs += res
    census = dict(texts=len(recs), with_passages=sum(r['n'] > 0 for r in recs), passages=sum(r['n'] for r in recs),
                  passage_words=sum(r['words'] for r in recs), usable=sum(r['usable'] for r in recs),
                  usable_passages=sum(r['n'] for r in recs if r['usable']), in_papers_jsonl=sum(r['key'] in meta for r in recs),
                  by_year={y: dict(texts=sum(1 for r in recs if r['year'] == y), usable=sum(1 for r in recs if r['year'] == y and r['usable']),
                                   passages=sum(r['n'] for r in recs if r['year'] == y and r['usable']))
                           for y in sorted({r['year'] for r in recs if r['year']})})
    pool = {r['key']: r for r in recs if 'cand' in r}
    rng = random.Random(V.SEED)
    by_school = defaultdict(list)
    for k in sorted(pool):
        by_school[pool[k]['school']].append(k)
    for s in by_school:
        rng.shuffle(by_school[s])
    npool = len(pool)
    q_src = {s: round(N_SRC * len(v) / npool) for s, v in by_school.items()}
    q_hum = {s: round(N_HUM * len(v) / npool) for s, v in by_school.items()}
    sources, humans = [], []
    for s, keys in sorted(by_school.items()):
        elig = {k: [(i, t) for i, t in pool[k]['cand'] if i > 0 and 60 <= len(t.split()) <= 400] if meta[k][2] else [] for k in keys}
        used = set()
        for k, (i, t) in rounds(keys, elig):
            if len(used) >= q_src[s]:
                break
            sources.append(dict(key=k, school=s, year=pool[k]['year'], title=meta[k][2], kind=pool[k]['kind'], split=V.split_of(k), pidx=i, text=t))
            used.add((k, i))
        rest = {k: [(i, t) for i, t in pool[k]['cand'] if (k, i) not in used] for k in keys}
        n = 0
        for k, (i, t) in rounds(keys, rest):
            if n >= q_hum[s]:
                break
            humans.append(dict(key=k, school=s, year=pool[k]['year'], kind=pool[k]['kind'], split=V.split_of(k), pidx=i, text=t)); n += 1
    rng.shuffle(sources)
    for i, x in enumerate(sources):
        x['sid'] = i; x['gen'] = V.GENS[i % 3]; x['task'] = V.TASKS[(i // 3) % 3]
    with open(V.DATA / 'sources.jsonl', 'w') as f:
        for x in sources:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    with open(V.DATA / 'humans.jsonl', 'w') as f:
        for x in humans:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    nheld = Counter()
    for part in ('cal', 'test'):
        with gzip.open(V.DATA / f'{part}_real.jsonl.gz', 'wt') as f:
            for k in sorted(pool):
                r = pool[k]
                if V.split_of(k) != part:
                    continue
                for i, t in enumerate(r.get('all') or []):
                    f.write(json.dumps(dict(key=k, school=r['school'], year=r['year'], kind=r['kind'], pidx=i, text=t), ensure_ascii=False) + '\n'); nheld[part] += 1
    stats = dict(splitter_sha=V.SPLITTER_SHA, census=census, pool_papers=npool, pool_by_school={s: len(v) for s, v in by_school.items()},
                 pool_by_split=Counter(V.split_of(k) for k in pool), pool_passages=sum(pool[k]['n'] for k in pool),
                 sources=len(sources), sources_by=Counter(f"{x['gen']}/{x['task']}" for x in sources), sources_by_split=Counter(x['split'] for x in sources),
                 sources_by_school=Counter(x['school'] for x in sources), source_papers=len({x['key'] for x in sources}),
                 humans=len(humans), humans_by_split=Counter(x['split'] for x in humans), humans_by_school=Counter(x['school'] for x in humans),
                 human_papers=len({x['key'] for x in humans}), real_passages=nheld,
                 real_papers=Counter(V.split_of(k) for k in pool if V.split_of(k) in ('cal', 'test')))
    json.dump(stats, open(V.DATA / 'prep_stats.json', 'w'), indent=1)
    print(json.dumps(stats))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--db', default=str(V.FULLTEXT)); ap.add_argument('-j', type=int, default=8)
    a = ap.parse_args()
    main(a.db, a.j)
