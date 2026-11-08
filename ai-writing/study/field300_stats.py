"""Estimators of the field-300 study on institution x year sufficient statistics (numpy/pandas only; tested on fixtures in tests/test_study_field300.py).

Unit of analysis: the institution (cluster), the paper is attributed to every cohort institution on its byline (full counting; fractional weights are a sensitivity).
Resampling: institutions with replacement, stratified by GRAS tier (study_labstats.weights); row 0 of W is the point estimate. A ratio measure is
M_t = sum_i w_i S[i,t] / sum_i w_i N[i,t]; a pair measure is sum_{i != j} w_i w_j X_ij / sum_{i != j} w_i w_j over eligible pairs.
"""
import numpy as np

import study_labstats as LS

YEARS = LS.YEARS


def tier_weights(tiers, B, seed):
    return LS.weights(np.asarray(tiers), B, seed)


def pair_draws(W, X, M, a=None, b=None):
    """Bootstrap draws of the weighted mean of X over eligible ordered pairs (i != j) with i in group a and j in group b (default: all). W: (B+1, L); X, M: (L, L)."""
    L = X.shape[0]
    a = np.ones(L, bool) if a is None else np.asarray(a, bool)
    b = np.ones(L, bool) if b is None else np.asarray(b, bool)
    Mm = (M.astype(float) * ~np.eye(L, dtype=bool))
    Wa, Wb = W * a, W * b
    with np.errstate(all='ignore'):
        num = np.einsum('bi,ij,bj->b', Wa, np.nan_to_num(X) * Mm, Wb)
        den = np.einsum('bi,ij,bj->b', Wa, Mm, Wb)
        return num / den


def mpd_cells(S, n, nmin):
    """Within-cell mean pairwise distance 1 - (|S|^2 - n) / (n (n - 1)) of unit vectors summed to S (L, T, d) with counts n (L, T); NaN below nmin papers."""
    ss = np.einsum('ltd,ltd->lt', S, S)
    with np.errstate(all='ignore'):
        m = 1.0 - (ss - n) / (n * (n - 1.0))
    return np.where(n >= nmin, m, np.nan)


def cross_distance(S, n, C):
    """Pair distance matrix of one year, 1 - (S_i.S_j - C_ij) / (n_i n_j - C_ij), where C_ij is the number of papers shared by institutions i and j (their cosine
    to themselves is 1 and must not count as a cross pair). S: (L, d), n: (L,), C: (L, L) with C_ii = n_i."""
    G = S @ S.T
    nn = np.outer(n, n)
    with np.errstate(all='ignore'):
        D = 1.0 - (G - C) / (nn - C)
    return D


def jsd_matrix(P):
    """Jensen-Shannon divergence (bits) between the rows of P (n, s)."""
    P = np.asarray(P, np.float64)
    M = 0.5 * (P[:, None, :] + P[None, :, :])

    def H(x):
        with np.errstate(all='ignore'):
            return -np.sum(np.where(x > 0, x * np.log2(x), 0.0), axis=-1)
    return H(M) - 0.5 * (H(P)[:, None] + H(P)[None, :])


def rarefied_mix(counts, m, rng, reps=10):
    """Mean over `reps` draws of m papers without replacement of the topic mix (probabilities) of one cell; None if the cell has fewer than m papers."""
    counts = np.asarray(counts, np.int64)
    if counts.sum() < m:
        return None
    d = rng.multivariate_hypergeometric(counts, m, size=reps)
    return (d / m).mean(0), d


def entropy_bits(p):
    p = np.asarray(p, float)
    with np.errstate(all='ignore'):
        return float(-np.sum(np.where(p > 0, p * np.log2(p), 0.0)))


def holm(p):
    """Holm step-down adjusted p-values (array in the input order)."""
    p = np.asarray(p, float)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p):
    """Benjamini-Hochberg adjusted p-values (q-values)."""
    p = np.asarray(p, float)
    m = len(p)
    o = np.argsort(p)[::-1]
    out = np.empty(m)
    prev = 1.0
    for r, i in enumerate(o):
        k = m - r
        prev = min(prev, p[i] * m / k)
        out[i] = prev
    return out


def boot_p(draws, est):
    """Two-sided p-value of H0 'effect = 0' from the bootstrap standard error: 2 (1 - Phi(|est| / sd)). A percentile p-value cannot go below 1/(B+1) = 0.0025 at B = 400,
    which would make every Holm adjustment over >100 tests exceed 0.25; the normal-approximation p keeps the ranking of strong effects."""
    import math
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    if len(d) < 30 or not np.isfinite(est):
        return np.nan
    sd = float(np.std(d, ddof=1))
    if sd <= 0:
        return 0.0 if est != 0 else 1.0
    return float(math.erfc(abs(est) / sd / math.sqrt(2)))
