"""Statistics used across the AI-dose study (numpy/pandas only; tested on fixtures): ratio-of-sums cluster bootstrap, weighted OLS with
cluster-robust errors, within-group demeaning, rank-based bins."""
import numpy as np
import pandas as pd


def boot_ratio(num, den, clusters=None, B=1000, seed=0):
    """(estimate, lo, hi): sum(num)/sum(den) with a 95% bootstrap interval over clusters (rows when `clusters` is None)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    if clusters is not None:
        codes, _ = pd.factorize(np.asarray(clusters))
        num, den = np.bincount(codes, num), np.bincount(codes, den)
    n = len(num)
    est = num.sum() / den.sum() if den.sum() else float('nan')
    if n < 2 or not den.sum():
        return est, float('nan'), float('nan')
    rng = np.random.default_rng(seed)
    out = np.empty(B)
    for s in range(0, B, 100):
        k = min(100, B - s)
        w = rng.multinomial(n, np.full(n, 1.0 / n), size=k).astype(float)
        out[s:s + k] = (w @ num) / np.maximum(w @ den, 1e-12)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return est, float(lo), float(hi)


def demean(df, cols, by):
    """Subtract the group mean of `cols` within the groups `by` (list of column names); returns a copy (the within transformation of fixed effects)."""
    out = df.copy()
    g = out.groupby(by, observed=True)[cols]
    out[cols] = out[cols] - g.transform('mean')
    return out


def ols_cluster(y, X, clusters, w=None):
    """Weighted least squares with CR1 cluster-robust standard errors. X must include its constant if one is wanted.
    Returns (beta, se) as arrays. Collinear columns are handled by the pseudo-inverse."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], y * sw
    A = np.linalg.pinv(Xw.T @ Xw)
    beta = A @ Xw.T @ yw
    e = (yw - Xw @ beta)
    codes, _ = pd.factorize(np.asarray(clusters))
    G, n, k = codes.max() + 1, len(y), X.shape[1]
    S = np.zeros((G, k))
    np.add.at(S, codes, Xw * e[:, None])
    meat = S.T @ S
    c = (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
    V = c * A @ meat @ A
    return beta, np.sqrt(np.maximum(np.diag(V), 0))


def cluster_boot_coef(y, X, clusters, j, B=500, seed=0, w=None):
    """Bootstrap over clusters of coefficient j of the OLS of y on X: (estimate, lo, hi)."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    codes, _ = pd.factorize(np.asarray(clusters))
    G = codes.max() + 1
    idx = [np.where(codes == g)[0] for g in range(G)]
    beta = np.linalg.pinv(X.T @ X) @ X.T @ y if w is None else None
    if w is None:
        est = beta[j]
    else:
        sw = np.sqrt(w)
        est = (np.linalg.pinv((X * sw[:, None]).T @ (X * sw[:, None])) @ (X * sw[:, None]).T @ (y * sw))[j]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        pick = np.concatenate([idx[g] for g in rng.integers(0, G, G)])
        Xb, yb = X[pick], y[pick]
        if w is not None:
            sw = np.sqrt(np.asarray(w)[pick]); Xb, yb = Xb * sw[:, None], yb * sw
        vals.append((np.linalg.pinv(Xb.T @ Xb) @ Xb.T @ yb)[j])
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def dose_bins(x, edges=(0, 0.05, 0.25, 0.5, 1.0001), labels=('0-5%', '5-25%', '25-50%', '50-100%')):
    """Categorical dose bins on a share in [0, 1]; the lowest bin includes zero."""
    return pd.cut(pd.Series(np.asarray(x, float)), bins=list(edges), labels=list(labels), include_lowest=True, right=False)
