"""Measure 4 of the non-text sameness study: topic concentration across labs, extending the existing cross-lab divergence (study_analyze.py topics).

  sameness_topics.py run --id SNAP

(a) Concentration of OpenAlex primary topics (4.5k topics) and subfields (250) over the strict lab-paper rows of a year: HHI, Shannon entropy (bits) and effective number
    of topics 2^H, after binomial thinning to a fixed number of paper-lab rows per scope (growth of the corpus cannot move them), plus the share of rows on the 10 most
    frequent topics of the year. Samples: `all` papers with a topic, `cs` (primary field Computer Science).
(b) Cross-lab Jensen-Shannon divergence (bits) of subfield mixes, the design of `topics_crosslab_jsd` (labs rarefied to m = 10 papers, 10 replicates) made yearly:
    a lab enters a year with >= 10 papers with a topic; pairs are within a school or across schools; pairs that share a paper in the year are dropped. The existing
    table compares two pooled periods of labs present in both; this one gives the series, the placebo, the across-school pairs and the sensitivity without the partial schools.
    A higher JSD is more different, so direction = -1 (a fall means labs are more alike).
"""
import argparse
import time

import numpy as np
import pandas as pd
import scipy.sparse as sp

import sameness_common as SC
import sameness_refs as SR
import study_common as C

M_PAPERS = 10
REPS = 10


def hhi_ent_top(c, ktop=10):
    tot = c.sum(1, keepdims=True)
    with np.errstate(all='ignore'):
        p = c / tot
        hhi = (p ** 2).sum(1)
        ent = -np.nansum(np.where(p > 0, p * np.log2(p), 0), axis=1)
        top = -np.partition(-c, ktop, axis=1)[:, :ktop].sum(1) / tot[:, 0]
    return hhi, ent, top


def concentration(lp, pan, W, labs, level, sample, rng):
    col = {'topic': 'topic_name', 'subfield': 'topic_sub'}[level]
    ok = pan[pan[col].notna()]
    if sample == 'cs':
        ok = ok[ok['topic_field'].eq('Computer Science')]
    d = lp.merge(ok[['k', col]], on='k')
    li = {l: i for i, l in enumerate(labs)}
    d['lab_i'] = d['lab_id'].map(li)
    cats = {v: i for i, v in enumerate(sorted(d[col].unique()))}
    d['c'] = d[col].map(cats)
    T = len(SC.YEARS)
    sers, cons = [], []
    for sc, schools in SC.scope_schools():
        dd = d[d['school'].isin(schools)]
        if dd['lab_i'].nunique() < 20:
            continue
        per = {}
        for ti, y in enumerate(SC.YEARS):
            x = dd[dd['year'] == y]
            if x['lab_i'].nunique() < 15:
                continue
            labs_y = np.sort(x['lab_i'].unique())
            pos = {l: i for i, l in enumerate(labs_y)}
            U = sp.csr_matrix((np.ones(len(x)), (x['lab_i'].map(pos).to_numpy(), x['c'].to_numpy())), shape=(len(labs_y), len(cats)))
            per[ti] = (U.T.tocsr(), W[:, labs_y])
        if len(per) < 5:
            continue
        M_thin = int(0.9 * min(float(Ut.sum()) for Ut, _ in per.values()))
        V = {k: np.full((W.shape[0], T), np.nan) for k in ('hhi', 'entropy', 'eff_n', 'top10')}
        for ti, (Ut, Wy) in per.items():
            c = np.asarray((Ut @ Wy.T).T)                      # draws x categories
            pth = np.minimum(1.0, M_thin / c.sum(1))
            th = rng.binomial(np.rint(c).astype(np.int64), pth[:, None]).astype(float)
            h, e, t10 = hhi_ent_top(th)
            V['hhi'][:, ti], V['entropy'][:, ti], V['top10'][:, ti] = h, e, t10
            V['eff_n'][:, ti] = 2 ** e
        for k, arr in V.items():
            meta = dict(layer='topics', measure=f'topic_{level}_{k}', level=level, scope=sc, sample=sample, direction=-1 if k in ('entropy', 'eff_n') else 1, thin_rows=M_thin)
            s, c_ = SC.contrast_rows(meta, arr, center=True)
            sers.append(s)
            cons.append(c_)
    return sers, cons


def jsd_matrix(P):
    """Pairwise Jensen-Shannon divergence in bits between the rows of P (n x S), block by block."""
    n = len(P)

    def H(x):
        with np.errstate(all='ignore'):
            return -np.nansum(np.where(x > 0, x * np.log2(x), 0), axis=-1)
    hp = H(P)
    out = np.zeros((n, n))
    for a in range(0, n, 40):
        blk = P[a:a + 40]
        out[a:a + 40] = H((blk[:, None, :] + P[None, :, :]) / 2) - (hp[a:a + 40, None] + hp[None, :]) / 2
    return np.clip(out, 0, None)


def jsd_series(lp, pan, W, labs, sample, rng):
    ok = pan[pan['topic_sub'].notna()]
    if sample == 'cs':
        ok = ok[ok['topic_field'].eq('Computer Science')]
    d = lp.merge(ok[['k', 'topic_sub']], on='k')
    li = {l: i for i, l in enumerate(labs)}
    d['lab_i'] = d['lab_id'].map(li)
    if sample == 'stable':          # labs with >= 10 papers in at least 6 of the 10 years: the lab set no longer changes with the year
        n = d.groupby(['lab_i', 'year']).size()
        keep = (n >= M_PAPERS).groupby('lab_i').sum()
        d = d[d['lab_i'].isin(keep[keep >= 6].index)]
    subs = {v: i for i, v in enumerate(sorted(d['topic_sub'].unique()))}
    d['s'] = d['topic_sub'].map(subs)
    sch = d.drop_duplicates('lab_i').set_index('lab_i')['school']
    T = len(SC.YEARS)
    mats = {}
    for ti, y in enumerate(SC.YEARS):
        x = d[d['year'] == y]
        g = x.groupby('lab_i')
        n = g.size()
        el = n[n >= M_PAPERS].index.to_numpy()
        if len(el) < (10 if sample == 'stable' else 20):
            continue
        P = np.zeros((len(el), len(subs)))
        arrs = {l: v.to_numpy() for l, v in g['s']}
        for a, l in enumerate(el):
            for _ in range(REPS):
                P[a] += np.bincount(rng.choice(arrs[l], M_PAPERS, replace=False), minlength=len(subs)) / M_PAPERS
        P /= REPS
        ks = x[x['lab_i'].isin(el)].groupby('lab_i')['k'].apply(set)
        pos = {l: i for i, l in enumerate(el)}
        share = np.zeros((len(el), len(el)), bool)
        byk = {}
        for l in el:
            for k in ks[l]:
                byk.setdefault(k, []).append(pos[l])
        for v in byk.values():
            if len(v) > 1:
                share[np.ix_(v, v)] = True
        mats[ti] = (el, jsd_matrix(P), share)
    sers, cons = [], []
    for sc, schools in SC.scope_schools():
        for pt in ('within', 'across'):
            if pt == 'across' and sc not in ('ALL', 'EXCL_PARTIAL'):
                continue
            V = np.full((W.shape[0], T), np.nan)
            for ti, (el, Dm, share) in mats.items():
                s_el = sch.loc[el].to_numpy()
                ix = np.where(np.isin(s_el, schools))[0]
                if len(ix) < 5:
                    continue
                ss = s_el[ix]
                same = ss[:, None] == ss[None, :]
                M = ((same if pt == 'within' else ~same) & ~share[np.ix_(ix, ix)] & ~np.eye(len(ix), dtype=bool)).astype(float)
                if M.sum() < 20:
                    continue
                V[:, ti] = SR.draw_stats(W[:, el[ix]], Dm[np.ix_(ix, ix)], M)
            if not np.isfinite(V[0]).any():
                continue
            meta = dict(layer='topics', measure='topic_jsd_subfield', pairs=pt, scope=sc, sample=sample, direction=-1)
            s, c_ = SC.contrast_rows(meta, V)
            sers.append(s)
            cons.append(c_)
    return sers, cons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run'])
    ap.add_argument('--id', default='2026-11-08')
    ap.add_argument('--B', type=int, default=SC.B)
    a = ap.parse_args()
    t0 = time.time()
    res = C.results_dir(a.id)
    out = res / 'sameness' / 'tables'
    out.mkdir(parents=True, exist_ok=True)
    pan = pd.read_parquet(res / 'work' / 'panel.parquet', columns=['k', 'topic_name', 'topic_sub', 'topic_field'])
    lp = pd.read_parquet(res / 'work' / 'lab_papers.parquet')
    labs, sch, W = SC.weights_for(lp, a.B)
    rng = np.random.default_rng(SC.SEED + 13)
    S, K = [], []
    for sample in ('all', 'cs'):
        for level in ('topic', 'subfield'):
            s, c = concentration(lp, pan, W, labs, level, sample, rng)
            S += s
            K += c
            print(sample, level, flush=True)
        s, c = jsd_series(lp, pan, W, labs, sample, rng)
        S += s
        K += c
        print(sample, 'jsd', flush=True)
    s, c = jsd_series(lp, pan, W, labs, 'stable', rng)
    S += s
    K += c
    pd.concat(S).to_csv(out / 'sameness_topics_series.csv', index=False)
    pd.concat(K).to_csv(out / 'sameness_topics_contrasts.csv', index=False)
    print('seconds', round(time.time() - t0))


if __name__ == '__main__':
    main()
