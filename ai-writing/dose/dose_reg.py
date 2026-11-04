"""Fixed-effects regression for the dose designs (numpy/pandas; tested against synthetic data with known coefficients).

fit(df, y, x, controls=(), fe=(), cluster=None, weights=None)
    y ~ x + controls | fe, with the fixed effects absorbed by alternating projections (any number of one-way effects; pass a combined
    column such as lab_year for an interaction). `x` and `controls` are column names; a controls column of dtype object/category is
    expanded into dummies (first level dropped). Standard errors are CR1 cluster-robust over `cluster` (default: rows).
    `x` may also be a list of columns (dose-bin dummies): beta/se/lo/hi are then those of the first.
    Returns a dict: beta, se, lo, hi (the coefficient of x and its 95% normal interval), n, clusters, `coefs` and `ses` (all slopes).
"""
import numpy as np
import pandas as pd

import dose_stats as S


def _codes(s):
    return pd.factorize(s.astype(str))[0]


def absorb(M, codes_list, w=None, tol=1e-9, maxit=200):
    """Subtract the (weighted) group means of every column of M for each coding in turn until the change falls below tol."""
    M = np.array(M, float, copy=True)
    if not codes_list:
        return M
    w = np.ones(M.shape[0]) if w is None else np.asarray(w, float)
    for _ in range(maxit):
        before = M.copy()
        for c in codes_list:
            n = c.max() + 1
            sw = np.bincount(c, w, minlength=n)
            for j in range(M.shape[1]):
                mu = np.bincount(c, w * M[:, j], minlength=n) / np.maximum(sw, 1e-300)
                M[:, j] -= mu[c]
        if len(codes_list) == 1 or np.abs(M - before).max() < tol:
            break
    return M


def design(df, x, controls):
    xs = [x] if isinstance(x, str) else list(x)
    cols, names = [df[c].to_numpy(float) for c in xs], list(xs)
    for c in controls:
        if df[c].dtype == object or str(df[c].dtype) == 'category':
            d = pd.get_dummies(df[c].astype(str), prefix=c, drop_first=True, dtype=float)
            cols += [d[k].to_numpy() for k in d.columns]
            names += list(d.columns)
        else:
            cols.append(df[c].to_numpy(float)); names.append(c)
    return np.column_stack(cols), names


def fit(df, y, x, controls=(), fe=(), cluster=None, weights=None):
    xs = [x] if isinstance(x, str) else list(x)
    need = [y, *xs, *controls, *fe] + ([cluster] if cluster else []) + ([weights] if weights else [])
    d = df.dropna(subset=need).reset_index(drop=True)
    if len(d) < 10 or d[xs[0]].nunique() < 2:
        return dict(beta=np.nan, se=np.nan, lo=np.nan, hi=np.nan, n=len(d), clusters=0, coefs={}, ses={})
    X, names = design(d, x, controls)
    w = d[weights].to_numpy(float) if weights else None
    codes = [_codes(d[f]) for f in fe]
    M = absorb(np.column_stack([d[y].to_numpy(float), X]), codes, w)
    yy, XX = M[:, 0], M[:, 1:]
    keep = XX.std(0) > 1e-12
    if not fe:   # an intercept, since nothing absorbed the mean
        XX = np.column_stack([XX, np.ones(len(d))]); names = names + ['const']; keep = np.append(keep, True)
    if not keep[0]:
        return dict(beta=np.nan, se=np.nan, lo=np.nan, hi=np.nan, n=len(d), clusters=0, coefs={}, ses={})
    cl = d[cluster] if cluster else pd.Series(np.arange(len(d)))
    b, se = S.ols_cluster(yy, XX[:, keep], cl.to_numpy(), w)
    nm = [n for n, k in zip(names, keep) if k]
    return dict(beta=float(b[0]), se=float(se[0]), lo=float(b[0] - 1.96 * se[0]), hi=float(b[0] + 1.96 * se[0]), n=len(d),
                clusters=int(cl.nunique()), coefs=dict(zip(nm, b)), ses=dict(zip(nm, se)))


def boot_fit(df, y, x, cluster, controls=(), fe=(), nested=(), weights=None, B=200, seed=0):
    """Cluster bootstrap of fit(): resample `cluster` units with replacement and refit B times. A resampled copy of a cluster is a new unit, so fixed effects
    listed in `nested` (those nested in the cluster, such as lab or lab-year) are relabelled per copy; the other effects (year, topic, school) keep their codes.
    Returns (beta, lo, hi) with a percentile 95% interval; NaN interval when fewer than 10 clusters."""
    need = [y, *( [x] if isinstance(x, str) else list(x)), *controls, *fe, cluster] + ([weights] if weights else [])
    d = df.dropna(subset=need).reset_index(drop=True)
    est = fit(d, y, x, controls=controls, fe=fe, cluster=cluster, weights=weights)['beta']
    codes, uniq = pd.factorize(d[cluster].astype(str))
    G = len(uniq)
    if G < 10:
        return est, np.nan, np.nan
    groups = [np.where(codes == g)[0] for g in range(G)]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        draw = rng.integers(0, G, G)
        pick = np.concatenate([groups[g] for g in draw])
        copy = np.concatenate([np.full(len(groups[g]), i) for i, g in enumerate(draw)])
        b = d.iloc[pick].reset_index(drop=True)
        b['__c'] = copy
        for c in nested:
            b[c] = b[c].astype(str) + '#' + b['__c'].astype(str)
        r = fit(b, y, x, controls=controls, fe=fe, cluster='__c', weights=weights)['beta']
        if np.isfinite(r):
            vals.append(r)
    if len(vals) < 20:
        return est, np.nan, np.nan
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(est), float(lo), float(hi)
