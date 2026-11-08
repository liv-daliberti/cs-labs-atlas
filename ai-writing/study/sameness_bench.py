"""Measure 3 of the non-text sameness study: do labs cluster on the same benchmarks, datasets and methods?

  sameness_bench.py mine     --id SNAP        candidate lists for the dictionary review (OpenAlex keywords, mined capitalised names) -> tables/bench_candidates_*.csv
  sameness_bench.py abstract --id SNAP        dictionary hits in title + abstract of every panel paper -> work/mentions_abstract.parquet
  sameness_bench.py fulltext --id SNAP -j N   hits in the main body (see below) of every paper with a stored copy -> work/mentions_fulltext.parquet
  sameness_bench.py analyze  --id SNAP        concentration of the hits across labs, by year -> tables/sameness_bench_*.csv
  sameness_bench.py handcheck --id SNAP       30 random extractions with context (seed 20261108) -> tables/bench_handcheck_sample.csv (verdicts are added by hand)

Dictionary: sameness_dictionary.py (curated; Papers with Code is defunct since 2025-07 and nothing is scraped). A lab uses an entry in a year when one of its strict-membership
papers of that year mentions it (title + abstract; full text: at least twice in the main body after its first quarter, a proxy for methods and experiments because the section
store keeps no headings). Measures per scope and year, on the entry set `benchmarks + datasets` (bench, data), on `methods` (meth) and on all: HHI and Shannon entropy (bits) of
the entry mix, thinned binomially to a fixed number of lab-entry uses per scope, and the share of labs that use at least one of the year's top-5 / top-10 entries (`top5_labs`; `top5_cond` = among labs that use any entry of the group, which removes the rise in how often names appear at all; `any_labs` = share of labs using any entry).
Samples: `abstract` (papers with an abstract), `abstract_cs` (OpenAlex field Computer Science), `fulltext` (papers with a stored copy: coverage differs by year; secondary).
"""
import argparse
import json
import multiprocessing as mp
import re
import sqlite3
import time
import zlib

import numpy as np
import pandas as pd

import sameness_common as SC
import sameness_dictionary as D
import study_common as C

SEED_CHECK = 20261108
GROUPS = {'bench_data': ('bench', 'data'), 'meth': ('meth',), 'all': ('bench', 'data', 'meth')}
SAMPLES_B = ('abstract', 'abstract_cs', 'fulltext')


def paths(a):
    snap = C.snapshot_dir(a.id)
    res = C.results_dir(a.id)
    out = res / 'sameness'
    (out / 'tables').mkdir(parents=True, exist_ok=True)
    (out / 'work').mkdir(parents=True, exist_ok=True)
    return snap, res, out


def abstracts(snap, ks=None):
    fr = []
    for f in ('universe/oa_fields.sqlite', 'delta/oa_fields_delta.sqlite'):
        db = sqlite3.connect(f'file:{snap / f}?mode=ro', uri=True)
        fr.append(pd.read_sql('select id as k, title, abstract, keywords from works', db))
        db.close()
    d = pd.concat(fr).drop_duplicates('k', keep='last')
    return d if ks is None else d[d['k'].isin(ks)]


def cmd_mine(a):
    import collections
    snap, res, out = paths(a)
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k', 'topic_field', 'has_abs'])
    d = abstracts(snap).merge(pan, on='k')
    d = d[d['topic_field'].eq('Computer Science') & d['has_abs']]
    kw = collections.Counter()
    for s in d['keywords'].dropna():
        try:
            kw.update(set(x.lower() for x in json.loads(s)))
        except ValueError:
            pass
    pd.DataFrame(kw.most_common(1500), columns=['keyword', 'papers']).to_csv(out / 'tables' / 'bench_candidates_keywords.csv', index=False)
    tok = re.compile(r'\b(?:[A-Z][A-Za-z0-9]*[A-Z0-9][A-Za-z0-9\-]*|[A-Z][a-z]+(?:[- ][A-Z][A-Za-z0-9]+)+)\b')
    c = collections.Counter()
    for t in d['abstract']:
        c.update(set(tok.findall(t)))
    pd.DataFrame(c.most_common(2500), columns=['name', 'papers']).to_csv(out / 'tables' / 'bench_candidates_names.csv', index=False)
    print(json.dumps({'cs_abstracts': len(d)}))


def text_hits(m, text, minc):
    return {i: n for i, n in m.counts(text).items() if n >= minc}


def cmd_abstract(a):
    snap, res, out = paths(a)
    m = D.Matcher()
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k', 'has_abs'])
    d = abstracts(snap, set(pan['k']))
    rows = []
    for k, t, ab in zip(d['k'], d['title'], d['abstract']):
        if not isinstance(ab, str) or len(ab.split()) < 10:
            continue
        for i, n in m.counts(f'{t or ""}. {ab}').items():
            rows.append((k, i, n))
    df = pd.DataFrame(rows, columns=['k', 'e', 'n'])
    df.to_parquet(out / 'work' / 'mentions_abstract.parquet')
    # dictionary coverage: papers per entry
    cov = df.groupby('e')['k'].nunique().reindex(range(len(m.names))).fillna(0).astype(int)
    pd.DataFrame({'entry': m.names, 'kind': m.kinds, 'papers_abstract': cov.to_numpy()}).to_csv(out / 'tables' / 'bench_dictionary_coverage.csv', index=False)
    print(json.dumps({'papers_with_abstract': int((d['abstract'].fillna('').str.split().str.len() >= 10).sum()), 'papers_with_hit': int(df['k'].nunique()), 'hits': len(df)}))


def _ft(args):
    pid, blob = args
    try:
        t = zlib.decompress(blob).decode('utf-8', 'ignore')
    except zlib.error:
        t = blob.decode('utf-8', 'ignore') if isinstance(blob, bytes) else str(blob)
    w = t.split()
    t = ' '.join(w[len(w) // 4:])
    return pid, text_hits(_M, t, 2)


_M = None


def _init():
    global _M
    _M = D.Matcher()


def cmd_fulltext(a):
    snap, res, out = paths(a)
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k', 'paper_id'])
    want = set(pan['paper_id'].dropna())
    db = sqlite3.connect(f'file:{C.sources()["sections"] / "sections.sqlite"}?mode=ro', uri=True, check_same_thread=False)

    def gen():
        for pid, blob in db.execute('select paper_id, main from sections where main is not null'):
            if pid in want:
                yield pid, blob
    rows = []
    seen = 0
    with mp.Pool(a.j, initializer=_init) as pool:
        for pid, h in pool.imap_unordered(_ft, gen(), chunksize=64):
            seen += 1
            rows.extend((pid, i, n) for i, n in h.items())
    df = pd.DataFrame(rows, columns=['paper_id', 'e', 'n']).merge(pan.dropna(), on='paper_id')[['k', 'e', 'n', 'paper_id']]
    df.to_parquet(out / 'work' / 'mentions_fulltext.parquet')
    pd.DataFrame({'paper_id': sorted(want)}).to_parquet(out / 'work' / 'fulltext_wanted.parquet')
    print(json.dumps({'texts_scanned': seen, 'hits': len(df)}))


# ---------------------------------------------------------------- analysis


def hhi_entropy(c):
    tot = c.sum(1, keepdims=True)
    with np.errstate(all='ignore'):
        p = c / tot
        hhi = (p ** 2).sum(1)
        ent = -np.nansum(np.where(p > 0, p * np.log2(p), 0), axis=1)
    return hhi, ent


def analyze_sample(sample, lp, pan, mt, W, labs, kinds, rng):
    """Series and contrasts of every measure for one sample. mt: mention table (k, e)."""
    if sample == 'fulltext':
        ok = pan.loc[pan['has_ft'].fillna(False).astype(bool), 'k']
    elif sample == 'abstract_cs':
        ok = pan.loc[pan['has_abs'] & pan['topic_field'].eq('Computer Science'), 'k']
    else:
        ok = pan.loc[pan['has_abs'], 'k']
    ok = set(ok)
    li = {l: i for i, l in enumerate(labs)}
    d = lp[lp['k'].isin(ok)].copy()
    d['lab_i'] = d['lab_id'].map(li)
    mm = mt[mt['k'].isin(ok)]
    E = len(kinds)
    lab_used = d.merge(mm[['k', 'e']].drop_duplicates(), on='k').drop_duplicates(['lab_i', 'year', 'e'])
    T = len(SC.YEARS)
    sers, cons = [], []
    for sc, schools in SC.scope_schools():
        dd = d[d['school'].isin(schools)]
        lu = lab_used[lab_used['school'].isin(schools)]
        if dd['lab_i'].nunique() < 20:
            continue
        per_year = {}
        for ti, y in enumerate(SC.YEARS):
            labs_y = np.sort(dd.loc[dd['year'] == y, 'lab_i'].unique())
            if len(labs_y) < 15:
                continue
            pos = {l: i for i, l in enumerate(labs_y)}
            x = lu[lu['year'] == y]
            U = np.zeros((len(labs_y), E))
            if len(x):
                U[x['lab_i'].map(pos).to_numpy(), x['e'].to_numpy()] = 1
            per_year[ti] = (U, W[:, labs_y])
        if len(per_year) < 5:
            continue
        for g, kk in GROUPS.items():
            idx = np.where(np.isin(kinds, kk))[0]
            tot = {ti: float(U[:, idx].sum()) for ti, (U, Wy) in per_year.items()}
            if min(tot.values()) < 50:
                continue
            M_thin = int(0.9 * min(tot.values()))
            V = {k: np.full((W.shape[0], T), np.nan) for k in ('hhi', 'entropy', 'top5_labs', 'top10_labs', 'top5_cond', 'top10_cond', 'any_labs')}
            for ti, (U, Wy) in per_year.items():
                Ug = U[:, idx]
                c = Wy @ Ug                                        # draws x entries: lab-uses
                pth = np.minimum(1.0, M_thin / c.sum(1))
                th = rng.binomial(np.rint(c).astype(np.int64), pth[:, None]).astype(float)
                V['hhi'][:, ti], V['entropy'][:, ti] = hhi_entropy(th)
                order = np.argsort(-c[0])
                nlab = Wy.sum(1)
                anyl = Ug.max(1)
                for kx in (5, 10):
                    anyk = Ug[:, order[:kx]].max(1)
                    V[f'top{kx}_labs'][:, ti] = (Wy @ anyk) / nlab
                    V[f'top{kx}_cond'][:, ti] = (Wy @ anyk) / (Wy @ anyl)
                V['any_labs'][:, ti] = (Wy @ anyl) / nlab
            for k, arr in V.items():
                meta = dict(layer='benchmarks', measure=f'bench_{g}_{k}', group=g, scope=sc, sample=sample, direction=-1 if k == 'entropy' else 1, thin_uses=M_thin)
                s, c_ = SC.contrast_rows(meta, arr, center=True)
                sers.append(s)
                cons.append(c_)
        print(sample, sc, 'done', flush=True)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True)


def cmd_analyze(a):
    snap, res, out = paths(a)
    m = D.Matcher()
    kinds = np.array(m.kinds)
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k', 'has_abs', 'has_ft', 'topic_field', 'paper_id'])
    lp = pd.read_parquet(res / 'work' / 'lab_papers.parquet')
    labs, sch, W = SC.weights_for(lp, a.B)
    rng = np.random.default_rng(SC.SEED + 9)
    sers, cons = [], []
    for sample in SAMPLES_B:
        f = out / 'work' / ('mentions_fulltext.parquet' if sample == 'fulltext' else 'mentions_abstract.parquet')
        if not f.exists():
            print('missing', f)
            continue
        s, c = analyze_sample(sample, lp, pan, pd.read_parquet(f), W, labs, kinds, rng)
        sers.append(s)
        cons.append(c)
    pd.concat(sers).to_csv(out / 'tables' / 'sameness_bench_series.csv', index=False)
    pd.concat(cons).to_csv(out / 'tables' / 'sameness_bench_contrasts.csv', index=False)
    # coverage of each sample by year (papers, share of lab papers)
    cov = []
    for sample, col in (('abstract', 'has_abs'), ('fulltext', 'has_ft')):
        x = lp.merge(pan[['k', col]], on='k', how='left')
        cov.append(x.groupby('year')[col].mean().rename(sample))
    pd.concat(cov, axis=1).reset_index().to_csv(out / 'tables' / 'bench_sample_coverage.csv', index=False)
    print('done')


def cmd_handcheck(a):
    snap, res, out = paths(a)
    m = D.Matcher()
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k'])
    d = abstracts(snap, set(pan['k']))
    d = d[d['abstract'].fillna('').str.split().str.len() >= 10].sort_values('k')
    rng = np.random.default_rng(SEED_CHECK)
    rows = []
    order = rng.permutation(len(d))
    for ix in order:
        k, t, ab = d.iloc[ix][['k', 'title', 'abstract']]
        text = f'{t or ""}. {ab}'
        hs = m.hits(text)
        if not hs:
            continue
        i, s0, s1 = hs[int(rng.integers(len(hs)))]
        rows.append(dict(paper=k, entry=m.names[i], kind=m.kinds[i], matched=text[s0:s1], context=text[max(0, s0 - 70):s1 + 70].replace('\n', ' ')))
        if len(rows) == 30:
            break
    pd.DataFrame(rows).to_csv(out / 'tables' / 'bench_handcheck_sample.csv', index=False)
    print('sample of', len(rows), 'seed', SEED_CHECK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['mine', 'abstract', 'fulltext', 'analyze', 'handcheck'])
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--B', type=int, default=SC.B)
    a = ap.parse_args()
    t0 = time.time()
    globals()['cmd_' + a.cmd](a)
    print('seconds', round(time.time() - t0))


if __name__ == '__main__':
    main()
