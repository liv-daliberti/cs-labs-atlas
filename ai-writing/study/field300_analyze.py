"""Field-300 layers at the abstract level (owner 2026-11-08): the 12-school measures on all 300 GRAS CS&E universities, institution as cluster.

  field300_analyze.py ai                       abstract AI flag (v1 detector, the 12-school operating point) -> tables/f300_ai_*.csv
  field300_analyze.py topics                   LLM-topic share, subfield/topic entropy (rarefied), cross-institution topic JSD
  field300_analyze.py embed --model M          within-institution and cross-institution embedding distance (+ topic-residual for the headline model)
  field300_analyze.py sameness-prep            writes the sameness-shaped inputs (lab_papers, papers with reference lists, panel) under work/sameness
  field300_analyze.py overlap|concentration --sample refs10|journal    reference overlap / citation concentration (sameness_refs.py, institutions as labs)
  field300_analyze.py bench                    benchmark and method dictionary hits in abstracts -> concentration (sameness_bench.py, institutions as labs)
Every statistic is stored as institution x year sufficient statistics under work/stats (npz) so field300_hetero.py can recompute any group without new passes.
Estimators and intervals: field300_stats.py / study_labstats.py (cluster bootstrap over institutions, stratified by GRAS tier, B=400, percentile 95%);
pre = 2016-22, post = 2023-25, placebo = 2019-21 minus 2016-18; no 2026.
"""
import argparse
import json
import time

import numpy as np
import pandas as pd

import field300_common as F
import field300_stats as FS
import study_common as SC
import study_labstats as LS

B = 400
SEED = 20261108
NMIN_EMB = 20      # papers for an institution-year to enter an embedding distance
M_RARE = {'subfield': 50, 'topic': 100}   # rarefaction depth of the topic mixes
T = len(LS.YEARS)


def out_dirs():
    r = F.results_dir()
    (r / 'tables').mkdir(parents=True, exist_ok=True)
    s = F.work_dir() / 'stats'
    s.mkdir(parents=True, exist_ok=True)
    return r / 'tables', s


def institutions():
    return pd.read_parquet(F.work_dir() / 'institutions.parquet').sort_values('idx').reset_index(drop=True)


def draws(inst, B_=B):
    return FS.tier_weights(inst['tier'].to_numpy(), B_, SEED)


def frame(cols):
    """Paper x institution rows with the paper columns `cols` (full counting; w_frac is the fractional weight)."""
    w = F.work_dir()
    pap = pd.read_parquet(w / 'papers.parquet', columns=['work', 'year'] + [c for c in cols if c != 'year'])
    pi = pd.read_parquet(w / 'paper_inst.parquet', columns=['work', 'inst', 'w_frac'])
    return pi.merge(pap, on='work')


def ratio_layer(name, d, val, W, L, meta=None, save=True):
    """Full and fractional counting of the ratio measure `val` (NaN rows are not in the denominator): series, contrasts, and the stored S, N matrices."""
    sers, cons = [], []
    d = d[d[val].notna()].copy()
    d['_vw'] = d[val].astype(float) * d['w_frac']
    d['_w'] = d['w_frac'].astype(float)
    labs = np.arange(L)
    for counting, (num, den) in (('full', (val, None)), ('fractional', ('_vw', '_w'))):
        S, N, _ = LS.lab_year(d, 'inst', 'year', num, den, labs=labs)
        s, c = LS.tables(dict(measure=name, counting=counting, **(meta or {})), S, N, W)
        sers.append(s)
        cons.append(c)
        if save and counting == 'full':
            _, sdir = out_dirs()
            np.savez_compressed(sdir / f'{name}.npz', S=S, N=N)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True)


def write(tag, ser, con):
    tab, _ = out_dirs()
    ser.to_csv(tab / f'f300_{tag}_series.csv', index=False)
    con.to_csv(tab / f'f300_{tag}_contrasts.csv', index=False)
    print(tag, len(ser), len(con), flush=True)


# ---------------------------------------------------------------- AI flag
def abstract_scores():
    w = F.work_dir()
    fs = sorted((w / 'ai' / 'parts' / 'abstract').glob('f300-*.parquet'))
    if not fs:
        raise SystemExit('no detector parts under work/ai/parts/abstract (run the GPU detect array first)')
    p = pd.concat([pd.read_parquet(f, columns=['paper_id', 'p_v1', 'p_v2']) for f in fs]).drop_duplicates('paper_id')
    p['work'] = p['paper_id'].str[1:].astype(np.int64)
    thr = float(pd.read_parquet(SC.snapshot_dir('2026-11-08') / 'ai' / 'papers_v3.parquet', columns=['thr_abstract'])['thr_abstract'].dropna().iloc[0])
    p['flag'] = (p['p_v1'] >= thr).astype(float)
    return p[['work', 'p_v1', 'flag']], thr


def cmd_ai(a):
    inst = institutions()
    W = draws(inst)
    sc, thr = abstract_scores()
    d = frame(['abs_ok']).merge(sc, on='work', how='left')
    d['abs_flag'] = np.where(d['abs_ok'], d['flag'], np.nan)
    ser, con = ratio_layer('abs_flag', d, 'abs_flag', W, len(inst), dict(threshold=thr))
    write('ai', ser, con)
    cov = d.drop_duplicates('work').groupby('year').agg(papers=('work', 'size'), abs_ok=('abs_ok', 'sum'), scored=('flag', lambda x: x.notna().sum())).reset_index()
    cov.to_csv(out_dirs()[0] / 'f300_ai_coverage.csv', index=False)


# ---------------------------------------------------------------- topics
def topic_counts(d, col):
    """(L, T, K) paper counts per institution-year and topic id; ids in sorted order."""
    ids = np.sort(d[col].dropna().unique())
    ix = pd.Series(np.arange(len(ids)), index=ids)
    x = d[d[col].notna()]
    out = np.zeros((int(d['inst'].max()) + 1, T, len(ids)), np.int32)
    np.add.at(out, (x['inst'].to_numpy(), x['year'].to_numpy() - LS.YEARS[0], ix.loc[x[col]].to_numpy()), 1)
    return out, ids


def topic_cells(cnt, m, seed, reps=10):
    """Rarefied mixes per cell: P (L, T, K) float32 (NaN rows below m papers) and entropy (L, T) in bits (mean over the reps)."""
    rng = np.random.default_rng(seed)
    L, Tn, K = cnt.shape
    P = np.full((L, Tn, K), np.nan, np.float32)
    H = np.full((L, Tn), np.nan)
    for i in range(L):
        for t in range(Tn):
            r = FS.rarefied_mix(cnt[i, t], m, rng, reps)
            if r is None:
                continue
            p, dr = r
            P[i, t] = p
            H[i, t] = float(np.mean([FS.entropy_bits(x / m) for x in dr]))
    return P, H


def cmd_topics(a):
    inst = institutions()
    L = len(inst)
    W = draws(inst)
    tab, sdir = out_dirs()
    d = frame(['has_abs10', 'llm_text', 'subfield', 'topic'])
    d['llm'] = np.where(d['has_abs10'], d['llm_text'].astype(float), np.nan)
    ser, con = ratio_layer('llm_topic', d, 'llm', W, L)
    write('llm', ser, con)
    sers, cons = [], []
    for col, m in M_RARE.items():
        cnt, ids = topic_counts(d, col)
        P, H = topic_cells(cnt, m, SEED + m)
        ok = np.isfinite(H)
        Hn = np.where(ok, H, 0.0)
        np.savez_compressed(sdir / f'entropy_{col}.npz', S=Hn, N=ok.astype(float))
        s, c = LS.tables(dict(measure=f'entropy_{col}_m{m}', counting='full'), Hn, ok.astype(float), W)
        sers.append(s)
        cons.append(c)
        J = np.full((T, L, L), np.nan, np.float32)
        M = np.zeros((T, L, L), bool)
        for t in range(T):
            v = np.where(ok[:, t])[0]
            if len(v) < 10:
                continue
            J[t][np.ix_(v, v)] = FS.jsd_matrix(P[v, t])
            M[t][np.ix_(v, v)] = True
        np.savez_compressed(sdir / f'jsd_{col}.npz', D=J, M=M)
        V = np.full((W.shape[0], T), np.nan)
        for t in range(T):
            if M[t].sum() > 100:
                V[:, t] = FS.pair_draws(W, J[t], M[t])
        import sameness_common as SM
        s, c = SM.contrast_rows(dict(measure=f'jsd_{col}_m{m}', counting='full'), V)
        sers.append(s)
        cons.append(c)
        print(col, 'topics', len(ids), flush=True)
    write('topics', pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True))


# ---------------------------------------------------------------- embeddings
def load_vectors(model):
    """(work ids int64 sorted, X float16) of all parts of `model` under work/emb/parts/<model>/abstract."""
    ids, mats = [], []
    for f in sorted((F.work_dir() / 'emb' / 'parts' / model / 'abstract').glob('part_*.npz')):
        with np.load(f) as z:
            ids.append(np.array([int(s[1:]) for s in z['ids']], np.int64))
            mats.append(z['X'])
    if not ids:
        raise SystemExit(f'no embedding parts for {model}')
    ids = np.concatenate(ids)
    X = np.vstack(mats)
    ids, first = np.unique(ids, return_index=True)
    return ids, X[first]


def center_unit(X, mean=None):
    """Centre (global mean over the embedded papers) and unit-normalise in float32, in blocks (returns float32 array)."""
    n = X.shape[0]
    if mean is None:
        mean = np.zeros(X.shape[1], np.float64)
        for i in range(0, n, 200000):
            mean += X[i:i + 200000].astype(np.float64).sum(0)
        mean /= n
    out = np.empty(X.shape, np.float32)
    for i in range(0, n, 200000):
        b = X[i:i + 200000].astype(np.float32) - mean.astype(np.float32)
        out[i:i + 200000] = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return out


def residualise(Xn, groups, minn=30):
    """Subtract each group's centroid (groups with >= minn papers) and renormalise: the topic-residual variant (spread within OpenAlex subfield)."""
    R = Xn.copy()
    for g, ix in pd.Series(np.arange(len(groups))).groupby(groups).indices.items():
        if len(ix) >= minn and not (isinstance(g, float) and np.isnan(g)):
            R[ix] -= R[ix].mean(0)
    return R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-9)


def cell_sums(pi_rows, Xn, rows, L, nmin_cells=None):
    """S (L, T, d) float32 and n (L, T): per institution-year sums of the unit vectors. pi_rows: inst, year arrays aligned with `rows` (index into Xn)."""
    import scipy.sparse as sp
    inst, year = pi_rows
    S = np.zeros((L * T, Xn.shape[1]), np.float32)
    cell = inst.astype(np.int64) * T + (year - LS.YEARS[0])
    for i in range(0, len(rows), 200000):
        sl = slice(i, i + 200000)
        c = cell[sl]
        G = sp.csr_matrix((np.ones(len(c), np.float32), (c, np.arange(len(c)))), shape=(L * T, len(c)))
        S += G @ Xn[rows[sl]]
    n = np.bincount(cell, minlength=L * T).reshape(L, T).astype(float)
    return S.reshape(L, T, -1), n


def shared_counts(pi, L):
    """C[t] (L, L): papers shared by institutions i and j in year t (diagonal = papers of i), from the embedded paper x institution rows."""
    import scipy.sparse as sp
    out = []
    for t, y in enumerate(LS.YEARS):
        x = pi[pi['year'] == y]
        wk, wi = pd.factorize(x['work'])[0], x['inst'].to_numpy()
        P = sp.csr_matrix((np.ones(len(x)), (wk, wi)), shape=(wk.max() + 1 if len(x) else 1, L))
        out.append((P.T @ P).toarray())
    return out


def embed_one(pi, Xn, rows, inst, W, model, variant):
    L = len(inst)
    S, n = cell_sums((pi['inst'].to_numpy(), pi['year'].to_numpy()), Xn, rows, L)
    mpd = FS.mpd_cells(S, n, NMIN_EMB)
    ok = np.isfinite(mpd)
    sers, cons = [], []
    s, c = LS.tables(dict(measure=f'emb_within_{model}_{variant}', counting='full'), np.where(ok, mpd, 0.0), ok.astype(float), W)
    sers.append(s)
    cons.append(c)
    C = shared_counts(pi, L)
    D = np.full((T, L, L), np.nan, np.float32)
    M = np.zeros((T, L, L), bool)
    V = np.full((W.shape[0], T), np.nan)
    for t in range(T):
        v = ok[:, t]
        D[t] = FS.cross_distance(S[:, t], n[:, t], C[t])
        M[t] = np.outer(v, v)
        if M[t].sum() > 100:
            V[:, t] = FS.pair_draws(W, D[t], M[t])
    import sameness_common as SM
    s, c = SM.contrast_rows(dict(measure=f'emb_cross_{model}_{variant}', counting='full'), V)
    sers.append(s)
    cons.append(c)
    _, sdir = out_dirs()
    np.savez_compressed(sdir / f'emb_within_{model}_{variant}.npz', S=np.where(ok, mpd, 0.0), N=ok.astype(float))
    np.savez_compressed(sdir / f'emb_cross_{model}_{variant}.npz', D=D, M=M)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True)


def cmd_embed(a):
    inst = institutions()
    W = draws(inst)
    t0 = time.time()
    ids, X = load_vectors(a.model)
    d = frame(['abs_ok', 'subfield'])
    d = d[d['abs_ok']]
    pos = pd.Series(np.arange(len(ids)), index=ids)
    d = d[d['work'].isin(pos.index)].reset_index(drop=True)
    rows = pos.loc[d['work']].to_numpy()
    Xn = center_unit(X)
    sub = d.drop_duplicates('work').set_index('work')['subfield']
    print(a.model, 'papers embedded', len(ids), 'paper x institution rows', len(d), round(time.time() - t0), 's', flush=True)
    sers, cons = [], []
    s, c = embed_one(d, Xn, rows, inst, W, a.model, 'raw')
    sers.append(s)
    cons.append(c)
    if a.model == SC.HEADLINE_MODEL:
        R = residualise(Xn, sub.reindex(ids).to_numpy())
        s, c = embed_one(d, R, rows, inst, W, a.model, 'topic_residual')
        sers.append(s)
        cons.append(c)
    write(f'embed_{a.model}', pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['ai', 'topics', 'embed'])
    ap.add_argument('--model', default=SC.HEADLINE_MODEL)
    a = ap.parse_args()
    t0 = time.time()
    globals()['cmd_' + a.cmd](a)
    print(json.dumps(dict(cmd=a.cmd, seconds=round(time.time() - t0))))


if __name__ == '__main__':
    main()
