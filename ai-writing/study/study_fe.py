"""Within (fixed-effects) regression with cluster-robust intervals, numpy only: the estimator behind the three design layers (study_design_*.py).

`within` removes a group fixed effect (and optionally a group-specific linear trend) from y and the regressors by weighted least squares per group;
`ols_cluster` fits the demeaned regression and returns coefficients with a CR1 cluster-robust covariance (clusters = PIs).
The year dummies and interactions are explicit columns (at most a few hundred), so no alternating projections are needed.
"""
import numpy as np


def _gsum(codes, v, n):
    return np.bincount(codes, weights=v, minlength=n)


def within(M, codes, w=None, t=None):
    """Residuals of every column of M (n x k) after weighted group means (and, with t, group-specific linear trends in t) are removed.

    codes: integer group code per row (0..G-1). A group whose t has no variation keeps the group-mean-only residual.
    """
    M = np.asarray(M, float)
    if M.ndim == 1:
        M = M[:, None]
    n, k = M.shape
    G = int(codes.max()) + 1
    w = np.ones(n) if w is None else np.asarray(w, float)
    sw = _gsum(codes, w, G)
    sw[sw == 0] = 1.0
    out = np.empty_like(M)
    if t is None:
        for j in range(k):
            out[:, j] = M[:, j] - (_gsum(codes, w * M[:, j], G) / sw)[codes]
        return out
    t = np.asarray(t, float)
    tbar = _gsum(codes, w * t, G) / sw
    tc = t - tbar[codes]                       # centred within group: the 2x2 normal equations decouple
    stt = _gsum(codes, w * tc * tc, G)
    good = stt > 1e-9
    den = np.where(good, stt, 1.0)
    for j in range(k):
        v = M[:, j] - (_gsum(codes, w * M[:, j], G) / sw)[codes]
        b = np.where(good, _gsum(codes, w * tc * v, G) / den, 0.0)
        out[:, j] = v - b[codes] * tc
    return out


def ols_cluster(y, X, cluster, w=None, names=None):
    """Weighted OLS of y on X (already demeaned) with CR1 cluster-robust covariance. Returns dict(beta, se, cov, n, G, names)."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    w = np.ones(n) if w is None else np.asarray(w, float)
    Xw = X * w[:, None]
    A = X.T @ Xw
    Ainv = np.linalg.pinv(A)
    beta = Ainv @ (Xw.T @ y)
    e = y - X @ beta
    cl = np.unique(cluster, return_inverse=True)[1]
    G = cl.max() + 1
    S = np.zeros((G, k))
    np.add.at(S, cl, Xw * e[:, None])
    meat = S.T @ S
    cov = Ainv @ meat @ Ainv * (G / max(G - 1, 1))
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return dict(beta=beta, se=se, cov=cov, n=int(n), G=int(G), names=list(names) if names is not None else None)


def tcrit(G):
    try:
        from scipy import stats
        return float(stats.t.ppf(0.975, max(G - 1, 1)))
    except ImportError:      # pragma: no cover
        return 1.96


def wald(beta, cov, idx):
    """Wald chi-square test that beta[idx] == 0 -> (stat, df, p)."""
    idx = list(idx)
    b = beta[idx]
    V = cov[np.ix_(idx, idx)]
    stat = float(b @ np.linalg.pinv(V) @ b)
    df = len(idx)
    try:
        from scipy import stats
        p = float(stats.chi2.sf(stat, df))
    except ImportError:      # pragma: no cover
        p = float('nan')
    return stat, df, p


def fit(y, X, codes, cluster, w=None, t=None, names=None):
    """Remove the group effect (and trend) from y and X, then OLS with cluster-robust errors."""
    M = within(np.column_stack([y, X]), codes, w, t)
    r = ols_cluster(M[:, 0], M[:, 1:], cluster, w, names)
    r['tcrit'] = tcrit(r['G'])
    return r


def table(r, drop=()):
    """Coefficient rows (name, est, se, lo, hi) of a fit()."""
    rows = []
    for nm, b, s in zip(r['names'], r['beta'], r['se']):
        if nm in drop:
            continue
        rows.append(dict(term=nm, est=float(b), se=float(s), lo=float(b - r['tcrit'] * s), hi=float(b + r['tcrit'] * s)))
    return rows


def lincom(r, c):
    """Linear combination c'beta of a fit() with its cluster-robust standard error and interval: dict(est, se, lo, hi)."""
    c = np.asarray(c, float)
    est = float(c @ r['beta'])
    se = float(np.sqrt(max(c @ r['cov'] @ c, 0.0)))
    return dict(est=est, se=se, lo=est - r['tcrit'] * se, hi=est + r['tcrit'] * se)
