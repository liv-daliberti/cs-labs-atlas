"""Step 2: homogenization of writing style (dispersion, convergence, AI link, all-AI bound) -> RUN/tables/*.csv.

usage: style_analyze.py [--kind abstract|fulltext] [--model specter2_proximity] [--procs 8]
reads  RUN/features_{abstract,allai,fulltext}.parquet (style_extract.py), universe, OpenAlex subfields, the topic embedding, detector table
Style space: every feature z-scored on the 2016-2022 papers; two blocks (scalar features incl. MTLD, readability, punctuation, hedging, Kobak rate;
function-word frequencies) scaled to equal total weight; Euclidean distance. 'raw' = that space; 'resid' = after removing what topic predicts:
each feature regressed (OLS, fitted on 2016-2022 papers) on OpenAlex subfield dummies + 32 principal components of the paper's abstract embedding
(`--model`), and the residual used. Measures per stratum-year, size-matched draws of m papers (bootstrap of the pool, R draws):
  disp  mean distance to the draw's centroid    mpd  mean pairwise distance    conv  mean distance to the 2016-2021 corpus centroid
Effects: mean of 2023-2025 minus mean of 2016-2022 (post), and placebo breaks 2019/2020/2021 inside 2016-2021. Intervals: 2.5/97.5 percentiles of the draws.
"""
import argparse
import warnings

import numpy as np
import pandas as pd

import style_common as S

warnings.filterwarnings('ignore', category=RuntimeWarning)
YEARS = list(range(2016, 2026))
PRE = [y for y in YEARS if y <= 2022]
POST = [2023, 2024, 2025]
import os
R = int(os.environ.get("STYLE_R", 100))


def load_inputs(kind, model, tag_allai=True):
    import emb_load as EL
    import lineage_common as LC
    papers, lp = EL.universe()
    papers = EL.oa_topics(papers)
    feats = pd.read_parquet(S.RUN / f'features_{kind}.parquet')
    ai = pd.read_parquet(S.AI_TABLE)[['paper_id', 'ai_share', 'flag_abstract']].drop_duplicates('paper_id')
    d = papers.merge(feats, on='paper_id').merge(ai, on='paper_id', how='left')
    ids, X = LC.load_vectors(model, 'abstract')
    pos = {p: i for i, p in enumerate(ids)}
    keep = d['paper_id'].isin(pos).to_numpy()
    d = d[keep].reset_index(drop=True)
    Z = LC.unit(X)[[pos[p] for p in d['paper_id']]]
    rng = np.random.default_rng(S.C.SEED)
    sub = rng.choice(len(Z), min(20000, len(Z)), replace=False)
    _, _, Vt = np.linalg.svd(Z[sub] - Z[sub].mean(0), full_matrices=False)
    pcs = (Z - Z[sub].mean(0)) @ Vt[:32].T
    allai = pd.read_parquet(S.RUN / 'features_allai.parquet') if kind == 'abstract' and tag_allai else None
    return d, pcs, allai, lp


def topic_fit(Xz, d, pcs, pre_mask):
    """Topic design (OpenAlex subfield dummies, subfields with < 30 pre papers fall back to their field, + embedding PCs) and OLS coefficients fitted on pre rows."""
    sf = d['oa_subfield'].fillna('NA').astype(str).to_numpy()
    cnt = pd.Series(sf[pre_mask]).value_counts()
    big = set(cnt[cnt >= 30].index)
    lab = np.where(pd.Series(sf).isin(big), sf, 'field:' + d['oa_field'].fillna('NA').astype(str).to_numpy())
    cats, inv = np.unique(lab, return_inverse=True)
    D = np.zeros((len(d), len(cats) + pcs.shape[1]), np.float32)
    D[np.arange(len(d)), inv] = 1
    D[:, len(cats):] = pcs
    beta, *_ = np.linalg.lstsq(D[pre_mask], Xz[pre_mask], rcond=1e-6)
    return D, beta


def blocks(Xz, scal_idx, fw_idx):
    out = np.zeros_like(Xz)
    out[:, scal_idx] = Xz[:, scal_idx] / np.sqrt(len(scal_idx))
    out[:, fw_idx] = Xz[:, fw_idx] / np.sqrt(len(fw_idx))
    return out


def draw_stats(V, c_pre, m, R, rng, pool):
    """V: dict variant -> matrix; pool: row indices. -> dict variant -> (R, 3) disp, mpd, conv; the same bootstrap draws for every variant."""
    res = {k: np.zeros((R, 3)) for k in V}
    for r in range(R):
        rs = rng.choice(pool, len(pool), replace=True)
        pick = rs[rng.permutation(len(rs))[:m]]
        for k, M in V.items():
            A = M[pick]
            ctr = A.mean(0)
            disp = np.linalg.norm(A - ctr, axis=1).mean()
            sq = (A * A).sum(1)
            G = np.sqrt(np.clip(sq[:, None] + sq[None, :] - 2 * A @ A.T, 0, None))
            mpd = G.sum() / (m * (m - 1))
            res[k][r] = (disp, mpd, np.linalg.norm(A - c_pre, axis=1).mean())
    return res


def year_table(V, years, c_pre, mask, m, rng, minpool, R=R):
    """dict variant -> array (n_years, R, 3), or None when some year has fewer than `minpool` papers."""
    pools = [np.flatnonzero(mask & (years == y)) for y in YEARS]
    if min(len(p) for p in pools) < minpool:
        return None
    out = {k: np.zeros((len(YEARS), R, 3)) for k in V}
    for i, p in enumerate(pools):
        st = draw_stats(V, c_pre, m, R, rng, p)
        for k in V:
            out[k][i] = st[k]
    return out


METRICS = ('disp', 'mpd', 'conv')


def effects(arr, base):
    """Rows of effect estimates from arr (n_years, R, 3): post and placebos, per metric."""
    rows = []
    yi = {y: i for i, y in enumerate(YEARS)}

    def contrast(a_years, b_years):
        return arr[[yi[y] for y in a_years]].mean(0) - arr[[yi[y] for y in b_years]].mean(0)       # (R, 3)
    designs = [('post', contrast(POST, PRE))] + [(f'placebo{b}', contrast(range(b, 2022), range(2016, b))) for b in (2019, 2020, 2021)]
    pre_level = arr[[yi[y] for y in PRE]].mean((0, 1))
    for name, c in designs:
        for j, mt in enumerate(METRICS):
            lo, hi = np.percentile(c[:, j], [2.5, 97.5])
            rows.append(dict(base, design=name, metric=mt, effect=float(c[:, j].mean()), lo=float(lo), hi=float(hi), pre_level=float(pre_level[j]),
                             rel=float(c[:, j].mean() / pre_level[j])))
    return rows


def series(arr, base):
    return [dict(base, year=y, **{m: float(arr[i, :, j].mean()) for j, m in enumerate(METRICS)}) for i, y in enumerate(YEARS)]


def md_free_ci(x):
    return float(np.mean(x)), *np.percentile(x, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kind', default='abstract')
    ap.add_argument('--model', default='specter2_proximity')
    a = ap.parse_args()
    import style_features as F
    rng = np.random.default_rng(S.C.SEED)
    d, pcs, allai, lp = load_inputs(a.kind, a.model)
    cols = F.feature_names()
    scal = [i for i, c in enumerate(cols) if not c.startswith('fw_')]
    fwi = [i for i, c in enumerate(cols) if c.startswith('fw_')]
    keep = d['year'].between(S.Y0, S.Y1).to_numpy() & ~np.isnan(d[cols].to_numpy(float)).any(1)
    S.C.log(kind=a.kind, papers=len(d), usable=int(keep.sum()))
    d, pcs = d[keep].reset_index(drop=True), pcs[keep]
    X = d[cols].to_numpy(float)
    pre = (d['year'] <= 2022).to_numpy()
    mu, sd = X[pre].mean(0), X[pre].std(0) + 1e-9
    Xz = np.clip((X - mu) / sd, -4, 4)       # winsorized at 4 sd: a few odd texts (very short, all-caps, symbols) would otherwise dominate every dispersion
    Dm, beta = topic_fit(Xz, d, pcs, pre)
    Xr = Xz - Dm @ beta
    spaces = {'raw': blocks(Xz, scal, fwi), 'resid': blocks(Xr, scal, fwi)}
    years = d['year'].to_numpy()
    cpre = {k: v[years <= 2021].mean(0) for k, v in spaces.items()}
    T = S.RUN / 'tables'
    T.mkdir(parents=True, exist_ok=True)
    tag = a.kind
    out = {k: [] for k in ('corpus', 'corpus_series', 'school', 'field', 'ai_link', 'ai_diff', 'allai', 'allai_series', 'lab', 'feature_shift')}
    # 1. corpus
    for sp, V in spaces.items():
        arrs = year_table({'orig': V}, years, cpre[sp], np.ones(len(d), bool), 1000 if a.kind == 'abstract' else 500, rng, 1000 if a.kind == 'abstract' else 500)
        base = dict(kind=tag, space=sp, stratum='all')
        out['corpus'] += effects(arrs['orig'], base)
        out['corpus_series'] += series(arrs['orig'], base)
    # 2. schools and fields
    sch = lp.drop_duplicates(['paper_id', 'school']).groupby('school')['paper_id'].agg(set).to_dict()
    top_fields = d['oa_field'].value_counts().index[:10]
    for sp, V in spaces.items():
        for s_, ids in sch.items():
            m = d['paper_id'].isin(ids).to_numpy()
            arr = year_table({'orig': V}, years, cpre[sp], m, 150, rng, 300)
            if arr is not None:
                out['school'] += effects(arr['orig'], dict(kind=tag, space=sp, stratum=s_))
        for f_ in top_fields:
            arr = year_table({'orig': V}, years, cpre[sp], (d['oa_field'] == f_).to_numpy(), 150, rng, 300)
            if arr is not None:
                out['field'] += effects(arr['orig'], dict(kind=tag, space=sp, stratum=f_))
    S.C.log(stage='strata done')
    # 3. AI link: detector-flagged vs not flagged papers of the same year (flagged = flag_abstract for abstracts, ai_share >= 0.25 for full text)
    flag = (d['flag_abstract'] == 1).to_numpy() if a.kind == 'abstract' else (d['ai_share'] >= 0.25).to_numpy()
    scored = d['flag_abstract'].notna().to_numpy() if a.kind == 'abstract' else d['ai_share'].notna().to_numpy()
    for sp, V in spaces.items():
        draws = {}
        for y in YEARS:
            for nm, m in (('flagged', flag & scored), ('not_flagged', ~flag & scored)):
                pool = np.flatnonzero(m & (years == y))
                if len(pool) < 60:
                    continue
                st = draw_stats({'x': V}, cpre[sp], 60, R, rng, pool)['x']
                draws[(y, nm)] = st
                out['ai_link'].append(dict(kind=tag, space=sp, year=y, group=nm, n=len(pool), disp=st[:, 0].mean(), mpd=st[:, 1].mean(), conv=st[:, 2].mean(),
                                           disp_lo=np.percentile(st[:, 0], 2.5), disp_hi=np.percentile(st[:, 0], 97.5),
                                           mpd_lo=np.percentile(st[:, 1], 2.5), mpd_hi=np.percentile(st[:, 1], 97.5)))
        for name, yrs in (('post', POST), ('placebo2019-21', [2019, 2020, 2021])):
            ys = [y for y in yrs if (y, 'flagged') in draws and (y, 'not_flagged') in draws]
            if not ys:
                continue
            dd = np.mean([draws[(y, 'flagged')] - draws[(y, 'not_flagged')] for y in ys], 0)
            nn = np.mean([draws[(y, 'not_flagged')] for y in ys], 0)
            for j, mt in enumerate(METRICS):
                out['ai_diff'].append(dict(kind=tag, space=sp, design=name, years=len(ys), metric=mt, diff=float(dd[:, j].mean()), lo=float(np.percentile(dd[:, j], 2.5)),
                                           hi=float(np.percentile(dd[:, j], 97.5)), rel=float(dd[:, j].mean() / nn[:, j].mean())))
    # 4. all-AI rewrite (abstracts): the same papers, original against rewritten
    if allai is not None:
        al = d[['paper_id']].merge(allai, on='paper_id', how='left')
        okc = ~np.isnan(al[cols].to_numpy(float)).any(1)
        ci = np.flatnonzero(okc)
        Xa = np.clip((al.loc[okc, cols].to_numpy(float) - mu) / sd, -4, 4)
        sub = d.iloc[ci].reset_index(drop=True)
        Xar = Xa - Dm[ci] @ beta
        yc = years[ci]
        for sp, (Vo, Va) in {'raw': (blocks(Xz[ci], scal, fwi), blocks(Xa, scal, fwi)), 'resid': (blocks(Xr[ci], scal, fwi), blocks(Xar, scal, fwi))}.items():
            cp = cpre[sp]
            arr = year_table({'orig': Vo, 'allai': Va}, yc, cp, np.ones(len(ci), bool), 1000, rng, 1000)
            for nm, ar in (('orig', arr['orig']), ('allai', arr['allai']), ('gap', arr['orig'] - arr['allai'])):
                out['allai'] += effects(ar, dict(kind=tag, space=sp, variant=nm, stratum='all'))
                out['allai_series'] += series(ar, dict(kind=tag, space=sp, variant=nm))
            # feature-level shift caused by the rewrite (in sd units of the original corpus)
            if sp == 'raw':
                for j, c in enumerate(cols):
                    out['feature_shift'].append(dict(kind=tag, feature=c, what='allai_minus_orig', delta=float((Xa[:, j] - Xz[ci][:, j]).mean())))
    S.C.log(stage='allai done')
    # 5. features: post minus pre mean in sd units (raw and topic-residualized), normal-approximation interval
    for nm, M in (('raw', Xz), ('resid', Xr)):
        po = (years >= 2023)
        for j, c in enumerate(cols):
            x1, x0 = M[po, j], M[pre, j]
            se = np.sqrt(x1.var() / len(x1) + x0.var() / len(x0))
            out['feature_shift'].append(dict(kind=tag, feature=c, what=f'post_minus_pre_{nm}', delta=float(x1.mean() - x0.mean()), lo=float(x1.mean() - x0.mean() - 1.96 * se),
                                             hi=float(x1.mean() - x0.mean() + 1.96 * se)))
            if nm == 'raw':
                out['feature_shift'].append(dict(kind=tag, feature=c, what='sd_ratio_post_over_pre', delta=float(x1.std() / x0.std())))
    # 6. lab level: labs with >= 20 papers in both periods; 20-paper draws; mean change across labs with a bootstrap over labs; slope on the lab's post AI share
    if a.kind == 'abstract':
        lab_ids = lp.drop_duplicates(['paper_id', 'lab_id']).groupby('lab_id')['paper_id'].agg(list).to_dict()
        pos = {p: i for i, p in enumerate(d['paper_id'])}
        flag_arr = np.nan_to_num(d['flag_abstract'].to_numpy(float), nan=0.0)
        for sp, V in spaces.items():
            for design, (pa, pb) in {'post': (POST, PRE), 'placebo2019': ([2019, 2020, 2021], [2016, 2017, 2018])}.items():
                rows = []
                for lab, ids in lab_ids.items():
                    idx = np.array([pos[p] for p in ids if p in pos])
                    if len(idx) < 40:
                        continue
                    ya = idx[np.isin(years[idx], pa)]
                    yb = idx[np.isin(years[idx], pb)]
                    if len(ya) < 20 or len(yb) < 20:
                        continue
                    st = {}
                    for nm, ii in (('a', ya), ('b', yb)):
                        vals = []
                        for _ in range(30):
                            A = V[rng.choice(ii, 20, replace=False)]
                            sq = (A * A).sum(1)
                            Gm = np.sqrt(np.clip(sq[:, None] + sq[None, :] - 2 * A @ A.T, 0, None))
                            vals.append((np.linalg.norm(A - A.mean(0), axis=1).mean(), Gm.sum() / 380))
                        st[nm] = np.mean(vals, 0)
                    rows.append((lab, *(st['a'] - st['b']), flag_arr[ya].mean()))
                if len(rows) < 10:
                    continue
                arr = np.array([r[1:] for r in rows])
                for j, mt in enumerate(('disp', 'mpd')):
                    boots = [arr[rng.integers(0, len(arr), len(arr)), j].mean() for _ in range(1000)]
                    xs = arr[:, 2] - arr[:, 2].mean()
                    sl = [(lambda ii: ((arr[ii, 2] - arr[ii, 2].mean()) * (arr[ii, j] - arr[ii, j].mean())).sum() / max(((arr[ii, 2] - arr[ii, 2].mean()) ** 2).sum(), 1e-12))(rng.integers(0, len(arr), len(arr))) for _ in range(1000)]
                    b1 = float((xs * (arr[:, j] - arr[:, j].mean())).sum() / (xs ** 2).sum())
                    out['lab'].append(dict(kind=tag, space=sp, design=design, metric=mt, labs=len(arr), change=float(arr[:, j].mean()), lo=np.percentile(boots, 2.5), hi=np.percentile(boots, 97.5),
                                           dose_slope=b1, slope_lo=np.percentile(sl, 2.5), slope_hi=np.percentile(sl, 97.5)))
    for k, v in out.items():
        if v:
            pd.DataFrame(v).to_csv(T / f'{k}_{tag}.csv', index=False)
    import json
    json.dump(dict(kind=tag, papers=len(d), pre=int(pre.sum()), post=int((years >= 2023).sum()), topic_model=a.model, R=R,
                   allai_common=int(len(ci)) if allai is not None else None), open(T / f'meta_{tag}.json', 'w'))
    S.C.log(done=tag)


if __name__ == '__main__':
    main()
