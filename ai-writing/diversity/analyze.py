"""Analyses 1-5 of DESIGN-v2.md section 3, on lab_diversity*.csv and results/paper_lab_measures.csv.gz.

1 lab level   for each measure: y = post - pre (2023-2026 minus 2016-2022) of the lab's equal-size-draw value,
              x = the lab's post-period AI usage (ai_mean: share of papers flagged by the abstract detector, or mean
              paragraph ai_share once paragraph_scores.jsonl.gz exists). y and x are z-scored over the labs in the fit,
              so the slope is in SD of change per SD of AI usage. Huber M-estimator (c = 1.345, MAD scale, IRLS) with an
              intercept and controls: log n of the family's papers pre and post, school dummies. 95% CI: percentile
              bootstrap over labs (BOOT resamples); p_boot from the same; p_perm: x permuted within school (PERM times).
              Labs need >= 5 papers of the family in each period (the draw size) and >= 5 AI-scored post papers.
   specs      main; baseline (+ the pre-period level, for regression to the mean); topic (analysis 4: + fixed effects
              for the lab's modal 10-cluster abstract topic and the change in its LLM-topic share)
2 within lab  paper x lab rows of one period, outcome z-scored, regressed on the paper's AI flag with lab x year fixed
              effects (papers of several labs weighted 1/labs), SE clustered by lab. Outcomes: distance to the lab's
              centroid (abstract and full text), N1, L1, L4, S8, and L7 (marker words: a check on the detector).
              post: 2023-2026; post_topic: + 50-cluster topic fixed effects and the LLM-topic indicator;
              pre_placebo: 2016-2022, where every flag is a false positive (what the detector's errors alone produce)
3 placebo     analysis 1 with a fake break at 2019 (2016-2018 vs 2019-2022) and 2020 (2016-2019 vs 2020-2022), with the
              same x: no ChatGPT on either side, so these slopes are the null spread
5 per school  the main spec within each school with >= MIN_SCHOOL labs
-> results/slopes.csv, results/within.csv, results/lab_wide.csv, results/analysis.json
"""
import json, os, time, zlib
from multiprocessing import Pool
import numpy as np
import pandas as pd
import common as C
from lab_diversity import FAMILY_MEASURES

BOOT = int(os.environ.get('AIW_BOOT', 1000))
PERM = int(os.environ.get('AIW_PERM', 1000))
MIN_LABS, MIN_SCHOOL, MIN_AI = 20, 20, 5
FAMILY = {m: f for f, ms in FAMILY_MEASURES.items() for m in ms}
LABELS = {
    'S1_abs': 'S1 knowledge extent', 'S2_abs': 'S2 dispersion', 'S3_abs': 'S3 pairwise distance', 'S4_abs': 'S4 Vendi score',
    'S5_abs': 'S5 topic entropy', 'S6_abs': 'S6 effective topics', 'S7_abs': 'S7 Rao-Stirling',
    'S1_ft': 'S1 knowledge extent', 'S2_ft': 'S2 dispersion', 'S3_ft': 'S3 pairwise distance', 'S4_ft': 'S4 Vendi score',
    'S5_ft': 'S5 topic entropy', 'S6_ft': 'S6 effective topics', 'S7_ft': 'S7 Rao-Stirling', 'S8_ft': 'S8 within-paper spread',
    'L1': 'L1 MATTR', 'L2': 'L2 unigram entropy', 'L3': 'L3 TF-IDF homogeneity', 'L4': 'L4 trigram novelty',
    'L5_mean': 'L5 sentence length, mean', 'L5_sd': 'L5 sentence length, SD', 'L6': 'L6 readability spread',
    'L7': 'L7 LLM-marker words', 'L8': 'L8 compression ratio', 'fre': 'Flesch reading ease (mean)',
    'N1': 'N1 distance to field', 'N2': 'N2 new topics', 'C1': 'C1 venue entropy', 'C2': 'C2 reference overlap',
    'C3': 'C3 reference-age spread', 'C4': 'C4 self-lab references',
}
# +1: higher = more diverse / novel; -1: higher = more alike; 0: not a diversity direction
LABELS = {m: LABELS[m] for f in ('abs', 'ft', 'txt', 'ref') for m in LABELS if FAMILY[m] == f}  # tables and figures group by family
DIRECTION = {m: 1 for m in LABELS}
DIRECTION.update(L3=-1, C2=-1, C4=0, L7=0, L5_mean=0, fre=0)
FAMILY_TITLE = {'abs': 'Semantic, title + abstract', 'ft': 'Semantic, full text', 'txt': 'Lexical and stylistic, full text', 'ref': 'Citations'}
WITHIN = ['dist_abs', 'dist_ft', 'N1', 'L1', 'L4', 'S8_ft', 'N2', 'L7']
WITHIN_LABELS = {'dist_abs': 'distance to lab centroid (abstract)', 'dist_ft': 'distance to lab centroid (full text)', 'N1': 'N1 distance to field',
                 'L1': 'L1 MATTR', 'L4': 'L4 trigram novelty', 'S8_ft': 'S8 within-paper spread', 'N2': 'N2 new topics', 'L7': 'L7 LLM-marker words'}


# ------------------------------------------------------------------ estimators

def huber(X, y, c=1.345, iters=50):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(iters):
        r = y - X @ b
        s = np.median(np.abs(r - np.median(r))) / 0.6745
        if s <= 1e-12:
            break
        u = np.abs(r) / (c * s)
        w = np.where(u <= 1, 1.0, 1.0 / np.maximum(u, 1e-12))
        sw = np.sqrt(w)
        nb = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        if np.max(np.abs(nb - b)) < 1e-7:
            b = nb; break
        b = nb
    return b


def z(v):
    v = np.asarray(v, float)
    sd = v.std()
    return (v - v.mean()) / sd if sd > 0 else v * 0


def design(df, x, controls, dummies):
    cols = [np.ones(len(df)), z(df[x])]
    for c in controls:
        cols.append(z(df[c]))
    for d in dummies:
        lv = sorted(df[d].unique())
        for v in lv[1:]:
            cols.append((df[d] == v).astype(float).values)
    return np.column_stack(cols)


def fit_slope(df, y, x, controls, dummies, rng, strata=None):
    """Standardized Huber slope of y on x with bootstrap CI and within-strata permutation p."""
    X = design(df, x, controls, dummies)
    Y = z(df[y])
    b = huber(X, Y)[1]
    n = len(df)
    bs = []
    for _ in range(BOOT):
        i = rng.integers(0, n, n)
        sub = df.iloc[i]
        if sub[x].std() == 0 or sub[y].std() == 0:
            continue
        bs.append(huber(design(sub, x, controls, dummies), z(sub[y]))[1])
    bs = np.array(bs)
    perm = []
    xs = df[x].values
    groups = [np.flatnonzero(df[strata].values == g) for g in df[strata].unique()] if strata else [np.arange(n)]
    for _ in range(PERM):
        xp = xs.copy()
        for g in groups:
            xp[g] = xs[rng.permutation(g)]
        Xp = X.copy(); Xp[:, 1] = z(xp)
        perm.append(huber(Xp, Y)[1])
    perm = np.abs(np.array(perm))
    return dict(beta=float(b), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                p_boot=float(min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))), p_perm=float((1 + (perm >= abs(b)).sum()) / (1 + len(perm))), n_labs=n)


# ------------------------------------------------------------------ lab-level data

def wide(main, a='pre', b='post'):
    """One row per lab: every measure's pre / post value and the change, the family n, AI usage, topic, LLM share."""
    A = main[main.period == a].set_index('lab'); B = main[main.period == b].set_index('lab')
    labs = A.index.intersection(B.index)
    A, B = A.loc[labs], B.loc[labs]
    cols = {'school': A['school'], 'name': A['name'], 'topic10': A['topic10']}
    for m in LABELS:
        if m in A and m in B:
            cols[f'{m}_a'] = A[m]; cols[f'{m}_b'] = B[m]; cols[f'd_{m}'] = B[m] - A[m]
    for f in FAMILY_MEASURES:
        if f'n_{f}' in A:
            cols[f'logn_{f}_a'] = np.log(A[f'n_{f}'].clip(lower=1)); cols[f'logn_{f}_b'] = np.log(B[f'n_{f}'].clip(lower=1))
    cols['n_papers_a'] = A.n_papers; cols['n_papers_b'] = B.n_papers
    cols['d_llm'] = B.llm_share - A.llm_share
    out = pd.DataFrame(cols, index=labs)
    return out


def task_lab(args):
    m, spec, school, comp, seed = args
    W = G['wide'][comp]
    ai = G['ai_post']
    d = W.join(ai, how='inner')
    d = d[d.n_ai_post >= MIN_AI]
    if school != 'all':
        d = d[d.school == school]
    f = FAMILY[m]
    need = [f'd_{m}', 'ai_post', f'logn_{f}_a', f'logn_{f}_b']
    if f'd_{m}' not in d:
        return None
    d = d.dropna(subset=need)
    if len(d) < (MIN_SCHOOL if school != 'all' else MIN_LABS):
        return None
    controls = [f'logn_{f}_a', f'logn_{f}_b']
    dummies = ['school'] if school == 'all' else []
    if spec == 'baseline':
        controls.append(f'{m}_a'); d = d.dropna(subset=[f'{m}_a'])
    if spec == 'topic':
        dummies.append('topic10'); controls.append('d_llm'); d = d.dropna(subset=['d_llm'])
    r = fit_slope(d, f'd_{m}', 'ai_post', controls, dummies, np.random.default_rng([C.SEED, zlib.crc32(f'{m}|{spec}|{school}|{comp}'.encode())]),
                  strata='school' if school == 'all' else None)
    return dict(measure=m, family=f, label=LABELS[m], spec=spec if comp == 'main' else comp, school=school, **r)


G = {}


# ------------------------------------------------------------------ within-lab

def demean(M, groups, w):
    """Weighted within-group demeaning of the columns of M."""
    out = M.copy()
    codes, inv = np.unique(groups, return_inverse=True)
    sw = np.bincount(inv, weights=w)
    for j in range(M.shape[1]):
        mu = np.bincount(inv, weights=w * M[:, j]) / np.maximum(sw, 1e-12)
        out[:, j] = M[:, j] - mu[inv]
    return out


def within(df, y, x, fe, extra=None, cluster='lab'):
    """WLS of z(y) on x (+ extra columns) after lab x year demeaning; CR1 cluster-robust SE for x."""
    d = df.dropna(subset=[y, x]).copy()
    d = d[d.groupby(fe)[x].transform('nunique') > 1]  # only lab-years with both kinds of paper identify the contrast
    if len(d) < 50 or d[cluster].nunique() < 10:
        return None
    w = d['w'].values
    Y = z(d[y].values)
    cols = [d[x].astype(float).values]
    if extra:
        for c in extra:
            if c.startswith('topic'):
                for v in sorted(d[c].dropna().unique())[1:]:
                    cols.append((d[c] == v).astype(float).values)
            else:
                cols.append(d[c].astype(float).values)
    Xr = np.column_stack(cols)
    A = demean(np.column_stack([Y, Xr]), d[fe].values, w)
    yd, Xd = A[:, 0], A[:, 1:]
    keep = Xd.std(0) > 1e-12
    keep[0] = True
    Xd = Xd[:, keep]
    XtWX = Xd.T @ (Xd * w[:, None])
    inv = np.linalg.pinv(XtWX)
    b = inv @ (Xd.T @ (w * yd))
    e = yd - Xd @ b
    cl = d[cluster].values
    meat = np.zeros_like(XtWX)
    for g in np.unique(cl):
        s = cl == g
        u = (Xd[s] * (w[s] * e[s])[:, None]).sum(0)
        meat += np.outer(u, u)
    Gn, N, K = len(np.unique(cl)), len(d), Xd.shape[1]
    V = inv @ meat @ inv * (Gn / (Gn - 1)) * ((N - 1) / max(1, N - K))
    se = float(np.sqrt(V[0, 0]))
    return dict(beta=float(b[0]), se=se, lo=float(b[0] - 1.96 * se), hi=float(b[0] + 1.96 * se), n_rows=len(d),
                n_papers=int(d.key.nunique()), n_labs=int(d[cluster].nunique()), n_flagged=int(d.loc[d[x] > 0, 'key'].nunique()))


def within_lab(P, F, ai):
    P = P.copy()
    P['flag'] = P.key.map({k: float(v['flag']) for k, v in ai.items()})
    P['dose'] = P.key.map({k: float(v['dose']) for k, v in ai.items()})
    P = P.merge(F[['topic50_abs', 'llm']], left_on='key', right_index=True, how='left')
    P['llm'] = P.llm.astype(float)
    P['w'] = 1.0 / P.groupby('key').lab.transform('count')
    P['labyear'] = P.lab + '|' + P.year.astype(str)
    out = []
    for spec, per, extra in (('post', 'post', None), ('post_topic', 'post', ['topic50_abs', 'llm']), ('pre_placebo', 'pre', None)):
        Q = P[P.period == per]
        for y in WITHIN:
            if y not in Q:
                continue
            q = Q.dropna(subset=['topic50_abs']) if extra else Q
            r = within(q, y, 'flag', 'labyear', extra)
            if r:
                out.append(dict(outcome=y, label=WITHIN_LABELS[y], spec=spec, x='flag', **r))
            if G['ai_source'] == 'paragraph' and spec == 'post':
                r = within(q, y, 'dose', 'labyear', extra)
                if r:
                    out.append(dict(outcome=y, label=WITHIN_LABELS[y], spec=spec, x='dose', **r))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ main

def family_counts(P, F, ai_post, mn):
    """Labs and distinct papers (2016-2026) behind the lab-level fits of each family."""
    has = {'abs': 'has_abs', 'ft': 'has_ft', 'txt': 'has_txt', 'ref': 'has_refs'}
    out = {}
    for f, col in has.items():
        ms = [m for m in mn.measure if FAMILY[m] == f]
        if not ms:
            continue
        labs = set(ai_post.index)
        q = P[P.lab.isin(labs)]
        keys = set(q.key) & set(F.index[F[col].astype(bool)])
        out[f] = dict(labs_max=int(mn[mn.measure.isin(ms)].n_labs.max()), papers=len(keys))
    return out


def main(workers):
    t0 = time.time()
    main_ = pd.read_csv(C.ROOT / 'lab_diversity.csv')
    plac = pd.read_csv(C.ROOT / 'lab_diversity_placebo.csv')
    P = pd.read_csv(C.RES / 'paper_lab_measures.csv.gz')
    F = pd.read_parquet(C.DATA / 'paper_features.parquet').set_index('key')
    ai, src = C.load_ai()
    G['ai_source'] = src
    post = main_[main_.period == 'post'].set_index('lab')
    G['ai_post'] = pd.DataFrame(dict(ai_post=post.ai_mean, ai_high_post=post.ai_high, n_ai_post=post.n_ai))
    G['wide'] = {'main': wide(main_)}
    for comp in ('placebo2019', 'placebo2020'):
        G['wide'][comp] = wide(plac[plac.comparison == comp], 'early', 'late')
    measures = [m for m in LABELS if f'd_{m}' in G['wide']['main']]
    tasks = [(m, s, 'all', 'main', 0) for m in measures for s in ('main', 'baseline', 'topic')]
    tasks += [(m, 'main', 'all', comp, 0) for m in measures for comp in ('placebo2019', 'placebo2020')]
    tasks += [(m, 'main', sc, 'main', 0) for m in measures for sc in C.SCHOOLS]
    with Pool(workers) as pool:
        res = [r for r in pool.imap_unordered(task_lab, tasks, chunksize=1) if r]
    S = pd.DataFrame(res)
    order = {m: i for i, m in enumerate(LABELS)}
    S = S.sort_values(['school', 'spec', 'measure'], key=lambda c: c.map(order) if c.name == 'measure' else c)
    S['direction'] = S.measure.map(DIRECTION)
    S.to_csv(C.RES / 'slopes.csv', index=False)
    Wt = within_lab(P, F, ai)
    Wt.to_csv(C.RES / 'within.csv', index=False)
    lw = G['wide']['main'].join(G['ai_post'], how='left')
    lw.reset_index().rename(columns={'index': 'lab'}).to_csv(C.RES / 'lab_wide.csv', index=False)

    pooled = S[(S.school == 'all')]
    pl = pooled[pooled.spec.isin(['placebo2019', 'placebo2020'])]
    mn = pooled[pooled.spec == 'main']
    null95 = float(np.percentile(np.abs(pl.beta), 95)) if len(pl) else None
    ai_post = G['ai_post'].join(G['wide']['main'][['school']], how='inner')
    ai_post = ai_post[ai_post.n_ai_post >= MIN_AI]
    Fy = F[F.index.isin(ai.keys())].copy()
    Fy['flag'] = Fy.index.map({k: float(v['flag']) for k, v in ai.items()})
    summary = dict(
        ai_source=src, boot=BOOT, perm=PERM,
        papers=int(len(F)), papers_abs=int(F.has_abs.sum()), papers_txt=int(F.has_txt.sum()), papers_ft=int(F.has_ft.sum()),
        papers_refs=int(F.has_refs.sum()), papers_ai=int(F.index.isin(ai.keys()).sum()),
        coverage_by_school={s: dict(papers=int((F.school == s).sum()), abs=int(F[F.school == s].has_abs.sum()), txt=int(F[F.school == s].has_txt.sum()),
                                    ft=int(F[F.school == s].has_ft.sum()), refs=int(F[F.school == s].has_refs.sum())) for s in C.SCHOOLS},
        coverage_by_period={per: dict(papers=int(F.year.isin(list(r)).sum()), txt=int(F[F.year.isin(list(r))].has_txt.sum()),
                                      ft=int(F[F.year.isin(list(r))].has_ft.sum())) for per, r in (('pre', C.PRE), ('post', C.POST))},
        labs_total=len(C.load_papers()[1]), labs_rows=int(main_.lab.nunique()), labs_with_both_periods=int(len(G['wide']['main'])), labs_in_ai_analysis=int(len(ai_post)),
        labs_in_ai_analysis_by_school=ai_post.school.value_counts().to_dict(),
        ai_post_lab_quantiles={str(q): float(ai_post.ai_post.quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
        flagged_share_by_year={int(y): float(g.flag.mean()) for y, g in Fy.groupby('year')},
        null_abs_slope_95=null95, placebo_abs_slope_sd=float(pl.beta.std()) if len(pl) else None,
        main_beyond_null=[dict(measure=r.measure, beta=r.beta, lo=r.lo, hi=r.hi) for r in mn.itertuples() if null95 is not None and abs(r.beta) > null95],
        main_ci_excludes_zero=[dict(measure=r.measure, beta=r.beta, lo=r.lo, hi=r.hi, p_perm=r.p_perm) for r in mn.itertuples() if r.lo > 0 or r.hi < 0],
        l7_vs_ai_lab_corr=float(lw[['d_L7', 'ai_post']].dropna().corr().iloc[0, 1]) if 'd_L7' in lw else None,
        l7_by_flag_post={str(k): float(v) for k, v in Fy[Fy.year >= 2023].groupby('flag').L7.mean().items()},
        family_counts=family_counts(P, F, ai_post, mn),
        seconds=round(time.time() - t0))
    (C.RES / 'analysis.json').write_text(json.dumps(summary, indent=1, default=float))
    C.log(slopes=len(S), within=len(Wt), seconds=summary['seconds'], null95=null95, ci_excludes_zero=[d['measure'] for d in summary['main_ci_excludes_zero']])


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('-j', type=int, default=32)
    main(ap.parse_args().j)
