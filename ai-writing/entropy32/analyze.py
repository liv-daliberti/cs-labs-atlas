"""Continuous AI dose x knowledge entropy, 32 schools (owner 2026-11-23), on e32.py's build.

Knowledge entropy exactly as diversity/figures.py fig3_fulltext (Hao et al. Fig. 3, our operationalisation): SPECTER2 base full-text (main body)
vectors of the 2023-2025 papers, k-means with 50 clusters fitted on all of them, entropy (nats) of a sample's spread over the clusters, over
repeated equal-size draws; knowledge extent alongside. Two geometries, as before: 'euclidean' (raw vectors, the default) and 'cosine' (unit vectors,
so k-means is spherical k-means; extent = 1 - min cosine to the centroid).

The exposure is continuous: ai_share_main, the share of a paper's scored main-body passages detector v3 flags (0-1).

  curve     dose-response: papers with share 0, then sliding windows over the rank of the positive shares (WIN papers each, GRID centres); each
            window gives DRAWS draws of n papers (n equal for every window). 'adjusted' draws re-weight each window to the pooled school x year mix
            of the 2023-2025 papers (so a window is not just "2025 papers" or "one school"); 'raw' draws are uniform. -> curve_<metric>.csv
  paper     paper-level: topic surprisal -log p(cluster) under the pooled 2023-2025 cluster shares (its mean over a group is the cross-entropy
            that entropy is bounded by) regressed on the AI share with school x year and lab fixed effects, lab-clustered CR1 errors; and per school
            -> paper_<metric>.json, school_slopes_<metric>.csv
  lab       labs with >= LAB_MIN usable papers both in 2016-2022 and 2023-2025: entropy of LAB_N-paper draws (mean of 200) in each period, the
            change against the lab's mean post AI share; OLS with school fixed effects, lab-bootstrap interval -> labs_<metric>.csv, lab_<metric>.json
  map       t-SNE (cosine on the unit vectors) of up to MAP_N 2023-2025 papers -> map.parquet
  figure    -> figures/ai_dose_entropy.png (+ .pdf), figures/ai_dose_entropy_<metric>_detail.png
  check     the overlap with the sealed 2026-11-08 v3 table (same detector): per-paper agreement of ai_share_main
usage: analyze.py [all|curve|paper|lab|map|figure|check] [--id 20261123]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e32  # noqa: E402

SEED = 20261123
K = 50
POST = (2023, 2025)
PRE = (2016, 2022)
WIN, GRID, DRAWS = 3000, 36, 400
LAB_MIN, LAB_N = 8, 8
SCHOOL_MIN, SCHOOL_AI_MIN = 300, 50
MAP_N = 30000
METRICS = ('euclidean', 'cosine')


def load(a):
    w = e32.work_dir(a.id)
    df = pd.read_parquet(w / 'papers_scored.parquet')
    X = np.load(w / 'X_specter2_base.npy').astype(np.float32)
    df = df[df.has_emb & df.ai_share_main.notna()].copy()
    df['row'] = df['emb_row'].astype(int)
    df['lab'] = df['labs'].map(lambda s: (json.loads(s) or [None])[0])
    return w, df.reset_index(drop=True), X


def space(X, metric):
    return X / np.linalg.norm(X, axis=1, keepdims=True) if metric == 'cosine' else X


def clusters(w, df, X, metric):
    """k-means on the 2023-2025 papers (fit), labels for every paper (predict); cached."""
    from sklearn.cluster import KMeans
    f = w / 'analysis' / f'clusters_{metric}.npz'
    post = df.year.between(*POST).values
    tag = f'{len(df)}-{int(post.sum())}-{K}-{SEED}'
    if f.exists():
        z = np.load(f)
        if str(z['tag']) == tag:
            return z['labels'], z['centers']
    Z = space(X[df.row.values], metric)
    km = KMeans(K, n_init=3, random_state=SEED).fit(Z[post])
    lab = km.predict(Z)
    np.savez(f, labels=lab, centers=km.cluster_centers_, tag=tag)
    return lab, km.cluster_centers_


def ent(L):
    p = np.bincount(L, minlength=K) / len(L)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def ext(V, metric):
    c = V.mean(0)
    if metric == 'cosine':
        return float(1 - (V @ c).min() / np.linalg.norm(c))
    return float(np.sqrt(((V - c) ** 2).sum(1)).max())


def stage_curve(a):
    w, df, X = load(a)
    r = np.random.default_rng(SEED)
    post = df[df.year.between(*POST)].reset_index(drop=True)
    cell = post.home_school + ':' + post.year.astype(str)
    target = cell.value_counts(normalize=True)
    dose = post.ai_share_main.values
    pos = np.flatnonzero(dose > 0)
    pos = pos[np.argsort(dose[pos], kind='stable')]
    zero = np.flatnonzero(dose == 0)
    win = min(WIN, len(pos) // 4)
    centres = np.linspace(win // 2, len(pos) - win // 2 - 1, GRID).round().astype(int)
    windows = [('zero', zero)] + [(f'w{j:02d}', pos[max(0, c - win // 2): c + win // 2]) for j, c in enumerate(centres)]
    n = int(min(1000, 0.8 * min(len(ix) for _, ix in windows)))
    out = []
    for metric in METRICS:
        lab_all, _ = clusters(w, df, X, metric)
        lab = lab_all[df.year.between(*POST).values]
        Z = space(X[post.row.values], metric)
        for name, ix in windows:
            cw = cell.values[ix]
            share = pd.Series(cw).value_counts(normalize=True)
            p = (target.reindex(cw).values / share.reindex(cw).values)
            p = p / p.sum()
            for mode, prob in (('adjusted', p), ('raw', None)):
                E, X_ = [], []
                for _ in range(DRAWS):
                    i = r.choice(ix, n, replace=False, p=prob)
                    E.append(ent(lab[i])); X_.append(ext(Z[i], metric))
                E, X_ = np.array(E), np.array(X_)
                out.append(dict(metric=metric, mode=mode, window=name, n_papers=len(ix), n_draw=n, dose_median=float(np.median(dose[ix])),
                                dose_lo=float(dose[ix].min()), dose_hi=float(dose[ix].max()), year_mean=float(post.year.values[ix].mean()),
                                entropy=float(np.median(E)), entropy_lo=float(np.quantile(E, .025)), entropy_hi=float(np.quantile(E, .975)),
                                extent=float(np.median(X_)), extent_lo=float(np.quantile(X_, .025)), extent_hi=float(np.quantile(X_, .975))))
            print(json.dumps({k: out[-2][k] for k in ('metric', 'window', 'dose_median', 'entropy', 'n_draw')}), flush=True)
    pd.DataFrame(out).to_csv(w / 'analysis' / 'curve.csv', index=False)


def demean(y, groups, iters=50):
    """Within transform for several fixed effects by alternating projections."""
    y = y.astype(float).copy()
    for _ in range(iters):
        before = y.copy()
        for g in groups:
            y -= pd.Series(y).groupby(g).transform('mean').values
        if np.abs(y - before).max() < 1e-10:
            break
    return y


def fe_slope(y, x, groups, cluster):
    yt, xt = demean(y, groups), demean(x, groups)
    b = float((xt @ yt) / (xt @ xt))
    e = yt - b * xt
    s = pd.Series(xt * e).groupby(cluster).sum().values
    G, N = len(s), len(y)
    v = (s @ s) / (xt @ xt) ** 2 * G / (G - 1) * (N - 1) / (N - 2)
    return b, float(np.sqrt(v)), G


def stage_paper(a):
    w, df, X = load(a)
    res = {}
    for metric in METRICS:
        lab_all, _ = clusters(w, df, X, metric)
        m = df.year.between(*POST).values & df.lab.notna().values
        d = df[m].copy()
        L = lab_all[m]
        p = np.bincount(L, minlength=K) / len(L)
        d['surprisal'] = -np.log(p[L])
        x = d.ai_share_main.values * 10          # per 10 points of AI share
        cell = (d.home_school + ':' + d.year.astype(str)).values
        b, se, G = fe_slope(d.surprisal.values, x, [cell, d.lab.values], d.lab.values)
        b0, se0, _ = fe_slope(d.surprisal.values, x, [cell], d.lab.values)
        res[metric] = dict(papers=len(d), labs=G, slope_per_10pts_school_year_lab_fe=b, se=se, ci=[b - 1.96 * se, b + 1.96 * se],
                           slope_per_10pts_school_year_fe=b0, se_school_year=se0, ci_school_year=[b0 - 1.96 * se0, b0 + 1.96 * se0],
                           mean_surprisal=float(d.surprisal.mean()), pooled_entropy=float(-(p[p > 0] * np.log(p[p > 0])).sum()))
        rows = []
        for s, g in d.groupby('home_school'):
            if len(g) < SCHOOL_MIN or (g.ai_share_main > 0).sum() < SCHOOL_AI_MIN:
                continue
            bs, ses, Gs = fe_slope(g.surprisal.values, g.ai_share_main.values * 10, [g.year.astype(str).values, g.lab.values], g.lab.values)
            rows.append(dict(school=s, papers=len(g), labs=Gs, ai_any=float((g.ai_share_main > 0).mean()), slope=bs, se=ses, lo=bs - 1.96 * ses, hi=bs + 1.96 * ses))
        pd.DataFrame(rows).to_csv(w / 'analysis' / f'school_slopes_{metric}.csv', index=False)
        print(json.dumps({metric: res[metric]}), flush=True)
    (w / 'analysis' / 'paper.json').write_text(json.dumps(res, indent=1))


def stage_lab(a):
    w, df, X = load(a)
    r = np.random.default_rng(SEED)
    res = {}
    for metric in METRICS:
        lab_all, _ = clusters(w, df, X, metric)
        d = df.assign(cl=lab_all)[df.lab.notna()]
        rows = []
        for lab, g in d.groupby('lab'):
            pre, post = g[g.year.between(*PRE)], g[g.year.between(*POST)]
            if len(pre) < LAB_MIN or len(post) < LAB_MIN:
                continue
            hp = np.mean([ent(r.choice(pre.cl.values, LAB_N, replace=False)) for _ in range(200)])
            hq = np.mean([ent(r.choice(post.cl.values, LAB_N, replace=False)) for _ in range(200)])
            rows.append(dict(lab=lab, school=g.home_school.iloc[0], n_pre=len(pre), n_post=len(post), h_pre=hp, h_post=hq, dh=hq - hp,
                             ai_post=float(post.ai_share_main.mean()), ai_pre=float(pre.ai_share_main.mean())))
        L = pd.DataFrame(rows)
        L.to_csv(w / 'analysis' / f'labs_{metric}.csv', index=False)
        x, y = L.ai_post.values * 10, L.dh.values
        b, se, G = fe_slope(y, x, [L.school.values], L.school.values)
        bs = []
        for _ in range(500):
            i = r.integers(0, len(L), len(L))
            xt, yt = demean(x[i], [L.school.values[i]]), demean(y[i], [L.school.values[i]])
            bs.append((xt @ yt) / (xt @ xt) if (xt @ xt) > 0 else np.nan)
        res[metric] = dict(labs=len(L), slope_dh_per_10pts=b, boot_ci=[float(np.nanquantile(bs, .025)), float(np.nanquantile(bs, .975))],
                           mean_dh=float(L.dh.mean()), corr=float(np.corrcoef(x, y)[0, 1]))
        print(json.dumps({metric: res[metric]}), flush=True)
    (w / 'analysis' / 'lab.json').write_text(json.dumps(res, indent=1))


def stage_map(a):
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    w, df, X = load(a)
    r = np.random.default_rng(SEED)
    post = np.flatnonzero(df.year.between(*POST).values)
    ix = np.sort(r.choice(post, min(MAP_N, len(post)), replace=False))
    Z = space(X[df.row.values[ix]], 'cosine')
    Z = PCA(50, random_state=SEED).fit_transform(Z)
    Y = TSNE(2, perplexity=40, init='pca', random_state=SEED, n_jobs=-1).fit_transform(Z)
    lab_e, _ = clusters(w, df, X, 'cosine')
    pd.DataFrame(dict(k=df.k.values[ix], x=Y[:, 0], y=Y[:, 1], ai=df.ai_share_main.values[ix], year=df.year.values[ix], school=df.home_school.values[ix],
                      cl_cosine=lab_e[ix])).to_parquet(w / 'analysis' / 'map.parquet')


BANDS = [(0, 0, '0%'), (1e-9, 0.10, '<10%'), (0.10, 0.25, '10–25%'), (0.25, 0.50, '25–50%'), (0.50, 1.0, '50%+')]
BAND_N, BAND_MIN = 200, 250


def stage_timeband(a):
    """Owner 2026-11-23: time x %AI x entropy, colored by average citation age. Cells = publication year (2016-2025) x AI-share band (all schools
    pooled); per cell DRAWS draws of BAND_N papers (cells under BAND_MIN papers are left out), entropy over the 50 clusters fitted on 2023-2025;
    'adjusted' re-weights a cell to its year's school mix. Citation age of a cell = mean of its papers' average citation age (citeage.py),
    with a paper-bootstrap interval. -> analysis/timeband.csv"""
    w, df, X = load(a)
    ca = pd.read_parquet(w / 'citeage' / 'citeage.parquet')
    df = df.merge(ca[['k', 'cite_age_mean', 'n_refs_dated']], on='k', how='left')
    r = np.random.default_rng(SEED)
    s = df.ai_share_main.values
    band = np.full(len(df), -1)
    for j, (lo, hi, _) in enumerate(BANDS):
        band[(s == 0) if hi == 0 else ((s >= lo) & (s <= hi) if j == len(BANDS) - 1 else (s >= lo) & (s < hi))] = j
    out = []
    for metric in METRICS:
        lab, _ = clusters(w, df, X, metric)
        for y in range(e32.FIRST, e32.LAST + 1):
            yr = df.year.values == y
            target = df.home_school[yr].value_counts(normalize=True)
            for j, (_, _, name) in enumerate(BANDS):
                ix = np.flatnonzero(yr & (band == j))
                if len(ix) < BAND_MIN:
                    continue
                sch = df.home_school.values[ix]
                share = pd.Series(sch).value_counts(normalize=True)
                p = target.reindex(sch).values / share.reindex(sch).values
                p = p / p.sum()
                for mode, prob in (('adjusted', p), ('raw', None)):
                    E = np.array([ent(lab[r.choice(ix, BAND_N, replace=False, p=prob)]) for _ in range(DRAWS)])
                    age = df.cite_age_mean.values[ix]
                    age = age[~np.isnan(age)]
                    bs = [r.choice(age, len(age)).mean() for _ in range(200)] if len(age) else [np.nan]
                    out.append(dict(metric=metric, mode=mode, year=y, band=name, band_i=j, papers=len(ix), n_draw=BAND_N, band_min=BAND_MIN, ai_median=float(np.median(s[ix])),
                                    entropy=float(np.median(E)), entropy_lo=float(np.quantile(E, .025)), entropy_hi=float(np.quantile(E, .975)),
                                    cite_age=float(age.mean()) if len(age) else np.nan, cite_age_lo=float(np.quantile(bs, .025)), cite_age_hi=float(np.quantile(bs, .975)),
                                    cite_age_papers=int(len(age))))
                print(json.dumps({k: out[-2][k] for k in ('metric', 'year', 'band', 'papers', 'entropy', 'cite_age')}), flush=True)
    pd.DataFrame(out).to_csv(w / 'analysis' / 'timeband.csv', index=False)
    import figure
    figure.timeband(w)


HEAVY = 0.25          # "AI papers" in the two-group views: >= 25% of main-body passages flagged (the study's heavy-AI definition)
PAPER_MEASURES = [('surprisal_euclidean', 'topic surprisal · Euclidean (nats)'), ('surprisal_cosine', 'topic surprisal · cosine (nats)'),
                  ('dist_euclidean', 'distance to the field centroid · Euclidean'), ('dist_cosine', '1 − cosine to the field centroid'),
                  ('cite_age_mean', 'average citation age (years)')]


def wstats(v, w):
    m = np.average(v, weights=w)
    return float(m), float(np.sqrt(np.average((v - m) ** 2, weights=w)))


def stage_distshift(a):
    """Owner 2026-11-23: "change in distribution? non-AI mean, change in distribution for AI papers, show standard deviations" -> all three views.
    Paper-level measures (per paper): topic surprisal (-log share of its cluster among 2023-2025 papers) and distance to its year's centroid of all
    papers, in both geometries, and average citation age. Group-level: knowledge entropy over DRAWS draws of BAND_N papers (its SD is across draws).
      shift    2023-2025, each AI band vs the 0% papers: (band mean - non-AI mean) / non-AI SD with a paper bootstrap, and SD(band) / SD(non-AI);
               the band is re-weighted to the 0% papers' school x year mix -> analysis/distshift.csv
      dists    per-paper values of 2023-2025 for 0% and >= HEAVY papers -> analysis/paper_measures.parquet (also the source of the histograms)
      time     per year, 0% and >= HEAVY papers: mean and SD of each measure (cells >= 100 papers) -> analysis/dist_time.csv"""
    w, df, X = load(a)
    ca = pd.read_parquet(w / 'citeage' / 'citeage.parquet')
    df = df.merge(ca[['k', 'cite_age_mean']], on='k', how='left')
    r = np.random.default_rng(SEED)
    post = df.year.between(*POST).values
    labs = {}
    for metric in METRICS:
        lab, _ = clusters(w, df, X, metric)
        labs[metric] = lab
        p = np.bincount(lab[post], minlength=K) / post.sum()
        df[f'surprisal_{metric}'] = -np.log(p[lab])
        Z = space(X[df.row.values], metric)
        dist = np.empty(len(df))
        for y in df.year.unique():
            m = df.year.values == y
            c = Z[m].mean(0)
            dist[m] = 1 - (Z[m] @ c) / np.linalg.norm(c) if metric == 'cosine' else np.sqrt(((Z[m] - c) ** 2).sum(1))
        df[f'dist_{metric}'] = dist
    s = df.ai_share_main.values
    band = np.full(len(df), -1)
    for j, (lo, hi, _) in enumerate(BANDS):
        band[(s == 0) if hi == 0 else ((s >= lo) & (s <= hi) if j == len(BANDS) - 1 else (s >= lo) & (s < hi))] = j
    df['band'] = band
    cell = (df.home_school + ':' + df.year.astype(str)).values
    keep = ['k', 'year', 'home_school', 'ai_share_main', 'band'] + [m for m, _ in PAPER_MEASURES]
    df[post][keep].to_parquet(w / 'analysis' / 'paper_measures.parquet')
    base = post & (band == 0)
    tgt = pd.Series(cell[base]).value_counts(normalize=True)
    rows = []
    for j, (_, _, name) in enumerate(BANDS):
        g = post & (band == j)
        if g.sum() < 50:
            continue
        sh = pd.Series(cell[g]).value_counts(normalize=True)
        wt = np.nan_to_num(tgt.reindex(cell[g]).values / sh.reindex(cell[g]).values)
        for col, _ in PAPER_MEASURES:
            v0, v1 = df[col].values[base], df[col].values[g]
            ok0, ok1 = ~np.isnan(v0), ~np.isnan(v1) & (wt > 0)
            if ok0.sum() < 50 or ok1.sum() < 50:
                continue
            m0, s0 = float(np.mean(v0[ok0])), float(np.std(v0[ok0]))
            for mode, ww in (('adjusted', wt[ok1]), ('raw', np.ones(ok1.sum()))):
                m1, s1 = wstats(v1[ok1], ww)
                bs = []
                for _ in range(300):
                    i0 = r.integers(0, ok0.sum(), ok0.sum()); i1 = r.integers(0, ok1.sum(), ok1.sum())
                    a0 = v0[ok0][i0]; bm, _ = wstats(v1[ok1][i1], ww[i1])
                    bs.append((bm - a0.mean()) / a0.std())
                rows.append(dict(measure=col, band=name, band_i=j, mode=mode, n_ai=int(ok1.sum()), n_non=int(ok0.sum()), non_mean=m0, non_sd=s0, mean=m1, sd=s1,
                                 shift_sd=(m1 - m0) / s0, shift_lo=float(np.quantile(bs, .025)), shift_hi=float(np.quantile(bs, .975)), sd_ratio=s1 / s0))
        # knowledge entropy: equal-size draws (re-weighted the same way), SD across draws
        if j == 0 or g.sum() >= BAND_MIN:
            for metric in METRICS:
                ix = np.flatnonzero(g)
                pr = None if j == 0 else wt / wt.sum()
                E = np.array([ent(labs[metric][r.choice(ix, BAND_N, replace=False, p=pr)]) for _ in range(DRAWS)])
                rows.append(dict(measure=f'entropy_{metric}', band=name, band_i=j, mode='adjusted', n_ai=int(g.sum()), mean=float(E.mean()), sd=float(E.std())))
    D = pd.DataFrame(rows)
    for metric in METRICS:   # entropy shifts against the 0% draws
        m = D.measure == f'entropy_{metric}'
        z = D[m & (D.band == '0%')].iloc[0]
        D.loc[m, 'non_mean'], D.loc[m, 'non_sd'] = z['mean'], z['sd']
        D.loc[m, 'shift_sd'] = (D.loc[m, 'mean'] - z['mean']) / z['sd']
        D.loc[m, 'sd_ratio'] = D.loc[m, 'sd'] / z['sd']
    D.to_csv(w / 'analysis' / 'distshift.csv', index=False)
    heavy = post & (s >= HEAVY)
    sh = pd.Series(cell[heavy]).value_counts(normalize=True)
    wt = np.nan_to_num(tgt.reindex(cell[heavy]).values / sh.reindex(cell[heavy]).values)
    draws = {}
    for metric in METRICS:
        for grp, ix, pr in (('non', np.flatnonzero(base), None), ('ai', np.flatnonzero(heavy), wt / wt.sum())):
            draws[f'{metric}_{grp}'] = np.array([ent(labs[metric][r.choice(ix, BAND_N, replace=False, p=pr)]) for _ in range(DRAWS)])
    np.savez(w / 'analysis' / 'entropy_draws.npz', **draws)
    trows = []
    for y in range(e32.FIRST, e32.LAST + 1):
        for grp, gm in (('non-AI (0%)', band == 0), (f'AI (≥{int(HEAVY * 100)}%)', s >= HEAVY)):
            g = (df.year.values == y) & gm
            if g.sum() < 100:
                continue
            for col, _ in PAPER_MEASURES:
                v = df[col].values[g]; v = v[~np.isnan(v)]
                if len(v) >= 100:
                    trows.append(dict(year=y, group=grp, measure=col, n=len(v), mean=float(v.mean()), sd=float(v.std()),
                                      se=float(v.std() / np.sqrt(len(v)))))
            if g.sum() >= BAND_MIN:
                for metric in METRICS:
                    ix = np.flatnonzero(g)
                    E = np.array([ent(labs[metric][r.choice(ix, BAND_N, replace=False)]) for _ in range(DRAWS)])
                    trows.append(dict(year=y, group=grp, measure=f'entropy_{metric}', n=int(g.sum()), mean=float(E.mean()), sd=float(E.std()), se=np.nan))
    pd.DataFrame(trows).to_csv(w / 'analysis' / 'dist_time.csv', index=False)
    print(json.dumps(dict(shift_rows=len(D), time_rows=len(trows))))
    import figure
    figure.distshift(w)


def stage_check(a):
    w, df, _ = load(a)
    snap = Path(e32.P.HOMOGENIZATION_STUDY) / 'snapshots' / '2026-11-08' / 'ai' / 'papers_v3.parquet'
    old = pd.read_parquet(snap, columns=['paper_id', 'ai_share_main'])
    m = df.merge(old, on='paper_id', suffixes=('', '_v3')).dropna(subset=['ai_share_main', 'ai_share_main_v3'])
    res = dict(overlap=len(m), pearson=float(np.corrcoef(m.ai_share_main, m.ai_share_main_v3)[0, 1]),
               mean_abs_diff=float((m.ai_share_main - m.ai_share_main_v3).abs().mean()), identical_share=float((m.ai_share_main == m.ai_share_main_v3).mean()))
    (w / 'analysis' / 'check_v3.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['all', 'curve', 'paper', 'lab', 'map', 'figure', 'check', 'timeband', 'distshift'])
    ap.add_argument('--id', default='20261123')
    a = ap.parse_args()
    (e32.work_dir(a.id) / 'analysis').mkdir(exist_ok=True)
    for s in (['check', 'curve', 'paper', 'lab', 'map', 'figure'] if a.stage == 'all' else [a.stage]):
        if s == 'figure':
            import figure
            figure.main(e32.work_dir(a.id))
        else:
            globals()['stage_' + s](a)


if __name__ == '__main__':
    main()
