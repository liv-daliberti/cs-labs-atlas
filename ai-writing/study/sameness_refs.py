"""Measures 1 and 2 of the non-text sameness study: reference-list overlap between labs and citation concentration, by year 2016-2025.

  sameness_refs.py overlap --id SNAP [--sample refs10|journal]
  sameness_refs.py concentration --id SNAP [--sample refs10|journal]

Source: reference lists in the snapshot's universe/oa_extra.sqlite (the local OpenAlex snapshot; nothing is fetched). Papers with >= 10 listed references only (the
OpenAlex lists of repository papers vanish from 2022, so the unrestricted lists would measure indexing, not citing); sample `journal` keeps journal papers, whose lists
stay complete. A lab-year needs >= 2 such papers for the pairwise overlap, >= 1 for the concentration. Harvard, JHU and WashU have no lists in the store: they are in
the scopes but contribute no labs.

Overlap. For each year, lab sets = union of the references of the lab's papers. Pair statistics between labs i, j: Jaccard I/(a_i+a_j-I), cosine I/sqrt(a_i a_j) and the
bibliographic coupling count I (shared references). Pairs of labs that share a paper in the year are dropped (identical lists). Null: the (lab, reference) memberships
of the year are permuted across labs, every lab keeping its list size (duplicates inside a lab are dropped), `NULL_REPS` replicates, averaged; the null keeps each work's
popularity and each lab's size, so observed - null is the overlap beyond what popularity and size give. Within-school pairs and across-school pairs are separate measures.

Concentration. Per scope and year, f(w) = number of labs citing work w (binary per lab). Counts are thinned binomially to a fixed number of memberships per scope so that
growth in list size cannot move them (`thin_*` rows); the unthinned canonical measures use a threshold relative to the number of labs. Variants: all works; without the
100 works whose lab-frequency share rose most from pre to post ("rise100", the mega-cited LLM-era papers); without the 100 most cited works overall ("top100").
"""
import argparse
import json
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

import sameness_common as SC
import study_common as C
import study_labstats as LS

NULL_REPS = 5
ACROSS_SCOPES = ('ALL', 'EXCL_PARTIAL')   # scopes that also get the across-school pairs (field300_sameness.py sets it: its 'schools' are institutions and every pair is 'across')
MIN_PAPERS_PAIR = 2
TOP_K = 100


def build_year(lpy, refs_of):
    """Binary labs x refs matrix of a year plus bookkeeping. lpy: lab-paper rows of the year (k, lab_i). refs_of: dict k -> int array."""
    ks = lpy['k'].unique()
    pidx = {k: i for i, k in enumerate(ks)}
    arrs = [np.unique(refs_of[k]) for k in ks]
    lens = np.array([len(a) for a in arrs])
    allrefs = np.concatenate(arrs) if arrs else np.empty(0, np.int64)
    uref, inv = np.unique(allrefs, return_inverse=True)
    PR = sp.csr_matrix((np.ones(len(inv)), inv, np.concatenate([[0], np.cumsum(lens)])), shape=(len(ks), len(uref)))
    labs = np.sort(lpy['lab_i'].unique())
    li = {l: i for i, l in enumerate(labs)}
    LP = sp.csr_matrix((np.ones(len(lpy)), (lpy['lab_i'].map(li).to_numpy(), lpy['k'].map(pidx).to_numpy())), shape=(len(labs), len(ks)))
    LP.data[:] = 1
    Bm = (LP @ PR).tocsr()
    Bm.data[:] = 1
    return dict(labs=labs, LP=LP, B=Bm, refs=uref, npap=np.asarray(LP.sum(1)).ravel())


def pair_stats(Bm):
    """Dense (I, a) of a binary csr."""
    I = (Bm @ Bm.T).toarray()
    a = np.asarray(Bm.sum(1)).ravel()
    return I, a


def jac_cos(I, a):
    U = a[:, None] + a[None, :] - I
    with np.errstate(all='ignore'):
        return I / U, I / np.sqrt(a[:, None] * a[None, :])


def null_matrix(Bm, rng):
    """Permute the memberships of the year across labs; every lab keeps its list size (duplicates inside a lab collapse)."""
    perm = rng.permutation(Bm.indices)
    Bn = sp.csr_matrix((np.ones(len(perm)), perm, Bm.indptr.copy()), shape=Bm.shape)
    Bn.sum_duplicates()
    Bn.data[:] = 1
    return Bn


def overlap_year(yd, reps=NULL_REPS, seed=0, minp=MIN_PAPERS_PAIR):
    """Matrices of the eligible labs: dict with el (positions in yd['labs']), obs/null for jaccard, cosine, coupling, and the paper-sharing mask."""
    el = np.where(yd['npap'] >= minp)[0]
    if len(el) < 3:
        return None
    Bm = yd['B'][el]
    I, a = pair_stats(Bm)
    j, c = jac_cos(I, a)
    rng = np.random.default_rng(seed)
    nj = nc = ni = 0.0
    sizes = []
    for _ in range(reps):
        Bn = null_matrix(Bm, rng)
        In, an = pair_stats(Bn)
        jn, cn = jac_cos(In, an)
        nj = nj + jn / reps
        nc = nc + cn / reps
        ni = ni + In / reps
        sizes.append(an.sum() / a.sum())
    LPe = yd['LP'][el]
    share = (LPe @ LPe.T).toarray() > 0
    return dict(el=el, labs=yd['labs'][el], jac=j, cos=c, cpl=I.astype(float), jac_n=nj, cos_n=nc, cpl_n=ni, share=share, size_ratio=float(np.mean(sizes)))


def draw_stats(Wsub, X, M):
    """Weighted mean of X over pairs in M (zero diagonal) for every draw: (w' (X*M) w) / (w' M w)."""
    num = (Wsub @ (X * M) * Wsub).sum(1)
    den = (Wsub @ M * Wsub).sum(1)
    with np.errstate(all='ignore'):
        return num / den


STATS = ('jac', 'cos', 'cpl')


def run_overlap(lp, p, sample, labs, sch, W, out_tab):
    ok = SC.sample_mask(p, sample)
    refs_of = dict(zip(p.loc[ok, 'k'], p.loc[ok, 'refs']))
    d = lp[lp['k'].isin(refs_of)].copy()
    li = {l: i for i, l in enumerate(labs)}
    d['lab_i'] = d['lab_id'].map(li)
    T = len(SC.YEARS)
    res = {}
    diag = []
    for ti, y in enumerate(SC.YEARS):
        yd = build_year(d[d['year'] == y], refs_of)
        o = overlap_year(yd, seed=1000 + y)
        if o is None:
            continue
        o['gl'] = yd['labs'][o['el']]           # global lab indices
        res[ti] = o
        diag.append(dict(sample=sample, year=y, labs=len(o['el']), papers=int(d[d['year'] == y]['k'].nunique()), null_size_ratio=o['size_ratio']))
    sers, cons = [], []
    for sc, schools in SC.scope_schools():
        for pt in ('within', 'across'):
            if pt == 'across' and sc not in ACROSS_SCOPES:
                continue
            V = {f'{s}_{k}': np.full((W.shape[0], T), np.nan) for s in STATS for k in ('raw', 'null')}
            for ti, o in res.items():
                s_el = sch[o['gl']]
                ins = np.isin(s_el, schools)
                ix = np.where(ins)[0]
                if len(ix) < 3:
                    continue
                ss = s_el[ix]
                same = ss[:, None] == ss[None, :]
                M = (same if pt == 'within' else ~same) & ~o['share'][np.ix_(ix, ix)] & ~np.eye(len(ix), dtype=bool)
                if M.sum() < 20:
                    continue
                M = M.astype(float)
                Wsub = W[:, o['gl'][ix]]
                for s in STATS:
                    V[f'{s}_raw'][:, ti] = draw_stats(Wsub, np.nan_to_num(o[s][np.ix_(ix, ix)]), M)
                    V[f'{s}_null'][:, ti] = draw_stats(Wsub, np.nan_to_num(o[f'{s}_n'][np.ix_(ix, ix)]), M)
            if not np.isfinite(V['jac_raw'][0]).any():
                continue
            for s in STATS:
                R_, N_ = V[f'{s}_raw'], V[f'{s}_null']
                for nm, arr, direction in ((f'{s}_raw', R_, 1), (f'{s}_null', N_, 1), (f'{s}_excess', R_ - N_, 1), (f'{s}_ratio', R_ / N_, 1)):
                    meta = dict(layer='overlap', measure=f'ref_{nm}', pairs=pt, scope=sc, sample=sample, direction=direction)
                    a, b = SC.contrast_rows(meta, arr)
                    sers.append(a)
                    cons.append(b)
        print(sample, sc, 'done', flush=True)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True), pd.DataFrame(diag)


# ------------------------------------------------------------------ concentration
def hist_stats(h, top_frac=0.01):
    """Concentration statistics of a vector of counts given as its histogram h[v] = number of works with count v (v >= 1; h[0] ignored)."""
    h = h.astype(float).copy()
    h[0] = 0
    v = np.arange(len(h), dtype=float)
    n = h.sum()
    T = (v * h).sum()
    if n < 10 or T <= 0:
        return dict(hhi=np.nan, entropy=np.nan, gini=np.nan, top1pct=np.nan, top100=np.nan, n_works=n)
    hhi = (v * v * h).sum() / T ** 2
    nz = h > 0
    ent = np.log2(T) - (v[nz] * np.log2(v[nz]) * h[nz]).sum() / T
    # Gini by the Lorenz curve over distinct values, ascending
    F = np.cumsum(h) / n
    L = np.cumsum(v * h) / T
    F0 = np.concatenate([[0], F[:-1]])
    L0 = np.concatenate([[0], L[:-1]])
    gini = 1 - ((F - F0) * (L + L0)).sum()

    def top_share(k):
        k = min(k, n)
        cc = np.cumsum(h[::-1])
        i = int(np.searchsorted(cc, k))          # histogram index (from the top) where the k-th work sits
        val = len(h) - 1 - i
        above = cc[i] - h[val]
        mass = (v[val + 1:] * h[val + 1:]).sum() + (k - above) * val
        return mass / T
    return dict(hhi=hhi, entropy=ent, gini=gini, top1pct=top_share(int(np.ceil(top_frac * n))), top100=top_share(TOP_K), n_works=n)


CONC = ('hhi', 'entropy', 'gini', 'top1pct', 'top100')


def lab_cite_counts(d, year, refs_of):
    """(ref ids, number of labs citing, number of labs) of a year from lab-paper rows d (k, lab_i)."""
    x = d[d['year'] == year]
    if x.empty:
        return np.empty(0, np.int64), np.empty(0, int), 0
    pairs = [np.unique(refs_of[k]) for k in x['k']]
    labs = np.repeat(x['lab_i'].to_numpy(), [len(a) for a in pairs])
    r = np.concatenate(pairs)
    key = np.unique(np.stack([labs, r], 1), axis=0)
    ids, cnt = np.unique(key[:, 1], return_counts=True)
    return ids, cnt, x['lab_i'].nunique()


def mega_sets(d, refs_of):
    """rise100: the TOP_K works whose share of labs citing them rose most pre -> post; top100: the TOP_K most cited overall. Returns (rise_ids, top_ids, table)."""
    share = {}
    tot = pd.Series(dtype=float)
    for y in SC.YEARS:
        ids, cnt, nl = lab_cite_counts(d, y, refs_of)
        s = pd.Series(cnt / max(nl, 1), index=ids)
        share[y] = s
        if len(ids):
            tot = pd.Series(cnt, index=ids).add(tot, fill_value=0)
    S = pd.DataFrame(share).fillna(0)
    rise = S[LS.POST].mean(1) - S[LS.PRE].mean(1)
    rid = rise.sort_values(ascending=False).head(TOP_K).index.to_numpy()
    tid = tot.sort_values(ascending=False).head(TOP_K).index.to_numpy()
    tab = pd.DataFrame({'work': rid, 'rise': rise.loc[rid].to_numpy(), 'share_pre': S.loc[rid, LS.PRE].mean(1).to_numpy(), 'share_post': S.loc[rid, LS.POST].mean(1).to_numpy()})
    return rid, tid, tab


def run_concentration(lp, p, sample, labs, sch, W, tab_dir):
    ok = SC.sample_mask(p, sample)
    refs_of = dict(zip(p.loc[ok, 'k'], p.loc[ok, 'refs']))
    d = lp[lp['k'].isin(refs_of)].copy()
    li = {l: i for i, l in enumerate(labs)}
    d['lab_i'] = d['lab_id'].map(li)
    rise, top, mtab = mega_sets(d, refs_of)
    mtab.to_csv(tab_dir / f'ref_mega_works_{sample}.csv', index=False)
    variants = {'full': np.empty(0, np.int64), 'rise100': rise, 'top100': top}
    T = len(SC.YEARS)
    sers, cons = [], []
    rng = np.random.default_rng(SC.SEED + 5)
    for sc, schools in SC.scope_schools():
        dd = d[d['school'].isin(schools)]
        if dd['lab_i'].nunique() < 20:
            continue
        years = {}
        for ti, y in enumerate(SC.YEARS):
            x = dd[dd['year'] == y]
            if x['lab_i'].nunique() < 10:
                continue
            ks = x['k'].unique()
            pidx = {k: i for i, k in enumerate(ks)}
            arrs = [np.unique(refs_of[k]) for k in ks]
            uref, inv = np.unique(np.concatenate(arrs), return_inverse=True)
            PR = sp.csr_matrix((np.ones(len(inv)), inv, np.concatenate([[0], np.cumsum([len(a) for a in arrs])])), shape=(len(ks), len(uref)))
            lab_ids = np.sort(x['lab_i'].unique())
            lmap = {l: i for i, l in enumerate(lab_ids)}
            LP = sp.csr_matrix((np.ones(len(x)), (x['lab_i'].map(lmap).to_numpy(), x['k'].map(pidx).to_numpy())), shape=(len(lab_ids), len(ks)))
            LP.data[:] = 1
            A = (LP @ PR).tocsr()
            A.data[:] = 1
            years[ti] = (A.T.tocsr(), uref, W[:, lab_ids])
        if len(years) < 5:
            continue
        for vname, drop in variants.items():
            # fixed number of memberships to thin to: 90% of the smallest year (point estimate)
            tot = {}
            for ti, (At, uref, Ws) in years.items():
                keep = ~np.isin(uref, drop)
                tot[ti] = float(At[keep].sum())
            M_thin = int(0.9 * min(tot.values()))
            V = {f'{k}': np.full((W.shape[0], T), np.nan) for k in CONC}
            V.update({k: np.full((W.shape[0], T), np.nan) for k in ('canon5_share', 'canon5_n', 'canon5_labs')})
            for ti, (At, uref, Ws) in years.items():
                keep = ~np.isin(uref, drop)
                At_k = At[keep]
                for b0 in range(0, W.shape[0], 25):
                    Wc = Ws[b0:b0 + 25]
                    c = np.asarray(At_k @ Wc.T)                     # works x draws: weighted number of labs citing
                    nl = Wc.sum(1)
                    totc = c.sum(0)
                    for j in range(c.shape[1]):
                        cj = c[:, j]
                        nzc = cj[cj > 0]
                        # canonical works: cited by >= 5% of the labs (unthinned)
                        thr = 0.05 * nl[j]
                        big = nzc[nzc >= thr]
                        V['canon5_n'][b0 + j, ti] = len(big)
                        V['canon5_share'][b0 + j, ti] = big.sum() / nzc.sum()
                        V['canon5_labs'][b0 + j, ti] = big.mean() / nl[j] if len(big) else np.nan
                        thin = rng.binomial(nzc.astype(np.int64), min(1.0, M_thin / totc[j]))
                        st = hist_stats(np.bincount(thin))
                        for k in CONC:
                            V[k][b0 + j, ti] = st[k]
            for k, arr in V.items():
                meta = dict(layer='concentration', measure=f'cite_{k}', variant=vname, scope=sc, sample=sample, direction=1, thin_memberships=M_thin)
                a, b = SC.contrast_rows(meta, arr, center=True)
                sers.append(a)
                cons.append(b)
        print(sample, sc, 'done', flush=True)
    return pd.concat(sers, ignore_index=True), pd.concat(cons, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', choices=['overlap', 'concentration'])
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--sample', default='refs10', choices=SC.SAMPLES)
    ap.add_argument('--B', type=int, default=SC.B)
    ap.add_argument('--out', default=None, help='override output directory (tests)')
    a = ap.parse_args()
    snap = C.snapshot_dir(a.id)
    res = C.results_dir(a.id)
    out = (res / 'sameness') if not a.out else __import__('pathlib').Path(a.out)
    tab = out / 'tables'
    tab.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    p = SC.load_papers(snap, res)
    lp = pd.read_parquet(res / 'work' / 'lab_papers.parquet')
    labs, sch, W = SC.weights_for(lp, a.B)
    if a.part == 'overlap':
        s, c, dg = run_overlap(lp, p, a.sample, labs, sch, W, tab)
        s.to_csv(tab / f'sameness_overlap_series_{a.sample}.csv', index=False)
        c.to_csv(tab / f'sameness_overlap_contrasts_{a.sample}.csv', index=False)
        dg.to_csv(tab / f'sameness_overlap_diag_{a.sample}.csv', index=False)
    else:
        s, c = run_concentration(lp, p, a.sample, labs, sch, W, tab)
        s.to_csv(tab / f'sameness_conc_series_{a.sample}.csv', index=False)
        c.to_csv(tab / f'sameness_conc_contrasts_{a.sample}.csv', index=False)
    print(json.dumps({'part': a.part, 'sample': a.sample, 'rows': len(c), 'seconds': round(time.time() - t0)}))


if __name__ == '__main__':
    main()
