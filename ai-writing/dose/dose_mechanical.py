"""How much does AI wording alone move embeddings and novelty?  (the mechanical-shift confound; CPU, after dose_mech.py embed)

  dose_mechanical.py measure --model M     -> AI_SCORES/results/mech_<model>.parquet
For every source text with a rewrite (same content, other wording) the shift is measured in the space the novelty tables use (vectors centred on the universe mean
and normalized):
  cos     cosine between the human and the AI version (1 - cos is the position shift), and `coherence`: |mean shift vector| / mean |shift vector| (1 = every
          rewrite moves the same way, the signature of a style direction rather than noise)
  novelty the size-matched nearest-neighbour novelty (nov_nn_cap, nov_max_cap: distance to the 5 nearest / the nearest of a random pool of at most 2,000
          universe papers of the previous k years, in all papers and in the source's school) of the human and the AI version against the same pool;
          delta = AI - human, mean over rewrites with a bootstrap interval over sources
  Rows are by kind: abstract (rewritten abstracts, v1 tasks polish/outline), passage (rewritten body passages, v2 tasks polish/paraphrase/notes),
  fulltext_add (the full-text mean vector of 2017-2021 papers moved by the mean passage shift: a paper whose text is entirely AI-worded; additive approximation) and
  abstract_add (the same additive move applied to abstract vectors, which checks the approximation against the actual abstract rewrites).
The dose-effect correction subtracts delta for polish / paraphrase (content kept) from the dose coefficient; outline / notes (content re-expanded) bound it from above.
"""
import argparse
import json

import numpy as np
import pandas as pd

import dcommon as D
import dose_stats as S

KS = (1, 3, 5)
CAP = 2000
SAME = {'abstract': ('polish',), 'passage': ('polish', 'paraphrase')}


def unit(X, mu):
    Y = np.asarray(X, np.float32) - mu
    return Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-9)


def nov(Q, P, nn=5):
    """(nov_nn, nov_max) of each unit row of Q against the unit rows of P: 1 - mean of the top-nn cosines, 1 - the largest cosine."""
    S_ = Q @ P.T
    m = min(nn, S_.shape[1])
    top = np.partition(S_, S_.shape[1] - m, axis=1)[:, -m:] if S_.shape[1] > m else S_
    return 1 - top.mean(1), 1 - S_.max(1)


def pool_for(Zu, years, schools, y, k, school, rng):
    mask = (years >= y - k) & (years < y)
    if school is not None:
        mask &= np.array([school in s for s in schools])
    idx = np.where(mask)[0]
    if len(idx) < 50:
        return None
    if len(idx) > CAP:
        idx = rng.choice(idx, CAP, replace=False)
    return Zu[idx]


def deltas(Zh, Za, meta, Zu, years, schools, scope, k, seed=0):
    """Per-pair (nov_nn_cap, nov_max_cap) deltas for pairs `meta` (list of dicts with year, school); human vectors Zh (aligned to pairs), AI vectors Za."""
    rng = np.random.default_rng(seed)
    out = np.full((len(meta), 2), np.nan)
    ys = np.array([m['year'] for m in meta])
    sc = np.array([m['school'] for m in meta])
    groups = {(y, (s if scope == 'school' else None)) for y, s in zip(ys, sc)}
    for y, s in groups:
        sel = np.where((ys == y) & ((sc == s) if s is not None else True))[0]
        pool = pool_for(Zu, years, schools, int(y), k, s, rng)
        if pool is None or not len(sel):
            continue
        h = np.column_stack(nov(Zh[sel], pool))
        a = np.column_stack(nov(Za[sel], pool))
        out[sel] = a - h
    return out


def summarize(delta, keys, extra):
    rows = []
    for j, name in enumerate(('nov_nn_cap', 'nov_max_cap')):
        d = delta[:, j]
        ok = np.isfinite(d)
        if ok.sum() < 20:
            continue
        est, lo, hi = S.boot_ratio(d[ok], np.ones(ok.sum()), clusters=np.asarray(keys)[ok], B=400)
        rows.append(dict(measure=name, delta=est, lo=lo, hi=hi, n=int(ok.sum()), **extra))
    return rows


def measure(model, n_boot=400):
    import emb_load as L
    z = np.load(D.SCORES / 'mech' / f'{model}.npz', allow_pickle=False)
    papers, _ = L.universe()
    ids, X, _ = L.vectors(model, 'abstract')
    keep = np.isin(ids, list(set(papers['paper_id'])))
    mu = X[keep].mean(0)
    yr = papers.set_index('paper_id')
    pid = [i for i, k in zip(ids, keep) if k]
    Zu = unit(X[keep], mu)
    years = yr.loc[pid, 'year'].to_numpy()
    schools = yr.loc[pid, 'schools'].tolist()
    rows = []
    for kind, h_key, a_key, meta_key in (('abstract', 'abs_h', 'abs_ai', 'abs_meta'), ('passage', 'psg_h', 'psg_ai', 'psg_meta')):
        meta = json.loads(str(z[meta_key]))
        H, A = z[h_key].astype(np.float32), z[a_key].astype(np.float32)
        Hm = H[[m['h'] for m in meta]]
        Zh, Za = unit(Hm, mu), unit(A, mu)
        cosv = (Zh * Za).sum(1)
        shift = Za - Zh
        df = pd.DataFrame(meta)
        for (task, gen), idx in list(df.groupby(['task', 'gen']).groups.items()) + [((t, 'all'), np.where(df['task'] == t)[0]) for t in df['task'].unique()]:
            idx = np.asarray(idx)
            coh = float(np.linalg.norm(shift[idx].mean(0)) / np.linalg.norm(shift[idx], axis=1).mean())
            rows.append(dict(kind=kind, task=task, gen=gen, scope='-', k=0, measure='cos', delta=float(1 - cosv[idx].mean()), lo=np.nan, hi=np.nan, n=len(idx), coherence=coh))
            for scope in ('all', 'school'):
                for k in KS:
                    d = deltas(Zh[idx], Za[idx], [meta[i] for i in idx], Zu, years, schools, scope, k)
                    rows += summarize(d, [meta[i]['key'] for i in idx], dict(kind=kind, task=task, gen=gen, scope=scope, k=k))
        if kind == 'passage':
            same = df['task'].isin(SAME['passage']).to_numpy()
            dvec = (A[same] - Hm[same]).mean(0)
        else:
            same = df['task'].isin(SAME['abstract']).to_numpy()
            dvec_abs = (A[same] - Hm[same]).mean(0)
    # additive approximation on abstract vectors (check) and on full-text mean vectors
    ft_ids, FT, _ = L.vectors(model, 'fulltext') if 'fulltext' in __import__('models').MODELS[model]['kinds'] else ([], np.zeros((0, X.shape[1])), None)
    for kind, vecs, vid, d in (('abstract_add', X, ids, dvec_abs), ('abstract_add_psg', X, ids, dvec), ('fulltext_add', FT, ft_ids, dvec)):
        if len(vid) == 0:
            continue
        inu = set(yr.index)
        sel = np.array([i in inu for i in vid])
        V = vecs[sel]
        vpid = [i for i, s in zip(vid, sel) if s]
        vy = yr.loc[vpid, 'year'].to_numpy()
        mu_k = V.mean(0)
        pick = np.where(np.isin(vy, range(2017, 2022)))[0]
        pick = np.random.default_rng(0).choice(pick, min(3000, len(pick)), replace=False)
        Zk = unit(V, mu_k)
        Zh, Za = Zk[pick], unit(V[pick] + d, mu_k)
        meta = [dict(year=int(vy[i]), school=yr.loc[vpid[i], 'schools'][0], key=vpid[i]) for i in pick]
        vs = yr.loc[vpid, 'schools'].tolist()
        for scope in ('all', 'school'):
            for k in KS:
                dd = deltas(Zh, Za, meta, Zk, vy, vs, scope, k)
                rows += summarize(dd, [m['key'] for m in meta], dict(kind=kind, task='mean-shift', gen='all', scope=scope, k=k))
        rows.append(dict(kind=kind, task='mean-shift', gen='all', scope='-', k=0, measure='cos', delta=float(1 - (Zh * Za).sum(1).mean()), lo=np.nan, hi=np.nan, n=len(pick), coherence=np.nan))
    out = pd.DataFrame(rows)
    out.insert(0, 'model', model)
    out.to_parquet(D.RESULTS / f'mech_{model}.parquet', index=False)
    D.log(model=model, rows=len(out))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['measure'])
    ap.add_argument('--model', required=True)
    a = ap.parse_args()
    measure(a.model)
