"""Fixed-effects regression for the dose designs (numpy/pandas; tested against synthetic data with known coefficients).

fit(df, y, x, controls=(), fe=(), cluster=None, weights=None)
    y ~ x + controls | fe, with the fixed effects absorbed by alternating projections (any number of one-way effects; pass a combined
    column such as lab_year for an interaction). `x` and `controls` are column names; a controls column of dtype object/category is
    expanded into dummies (first level dropped). Standard errors are CR1 cluster-robust over `cluster` (default: rows).
    Returns a dict: beta, se, lo, hi (the coefficient of x and its 95% normal interval), n, clusters, and `coefs` (all slopes).
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
    cols, names = [df[x].to_numpy(float)], [x]
    for c in controls:
        if df[c].dtype == object or str(df[c].dtype) == 'category':
            d = pd.get_dummies(df[c].astype(str), prefix=c, drop_first=True, dtype=float)
            cols += [d[k].to_numpy() for k in d.columns]
            names += list(d.columns)
        else:
            cols.append(df[c].to_numpy(float)); names.append(c)
    return np.column_stack(cols), names


def fit(df, y, x, controls=(), fe=(), cluster=None, weights=None):
    need = [y, x, *controls, *fe] + ([cluster] if cluster else []) + ([weights] if weights else [])
    d = df.dropna(subset=need).reset_index(drop=True)
    if len(d) < 10 or d[x].nunique() < 2:
        return dict(beta=np.nan, se=np.nan, lo=np.nan, hi=np.nan, n=len(d), clusters=0, coefs={})
    X, names = design(d, x, controls)
    w = d[weights].to_numpy(float) if weights else None
    codes = [_codes(d[f]) for f in fe]
    M = absorb(np.column_stack([d[y].to_numpy(float), X]), codes, w)
    yy, XX = M[:, 0], M[:, 1:]
    if not fe:   # an intercept, since nothing absorbed the mean
        XX = np.column_stack([XX, np.ones(len(d))]); names = names + ['const']
    keep = XX.std(0) > 1e-12
    keep[0] = True if XX[:, 0].std() > 1e-12 else False
    if not keep[0]:
        return dict(beta=np.nan, se=np.nan, lo=np.nan, hi=np.nan, n=len(d), clusters=0, coefs={})
    cl = d[cluster] if cluster else pd.Series(np.arange(len(d)))
    b, se = S.ols_cluster(yy, XX[:, keep], cl.to_numpy(), w)
    nm = [n for n, k in zip(names, keep) if k]
    return dict(beta=float(b[0]), se=float(se[0]), lo=float(b[0] - 1.96 * se[0]), hi=float(b[0] + 1.96 * se[0]), n=len(d),
                clusters=int(cl.nunique()), coefs=dict(zip(nm, b)))
