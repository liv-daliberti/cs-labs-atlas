"""Entropy and interval maths for the topic and novelty tables (numpy only; tested on fixtures).

shannon(counts)             entropy in bits of a count vector
miller_madow(counts)        shannon + (K - 1) / (2 n ln 2): the first-order bias correction for n papers over K occupied topics
rarefied(counts, m, ...)    mean entropy of `reps` random draws of m papers (without replacement) from the counts: two groups of different size
                            are compared at the same m, so a lab with more papers does not look more diverse for that reason alone
cluster_bootstrap_mean      mean of a value by group with a bootstrap over clusters (labs): papers of one lab are not independent
"""
import numpy as np


def shannon(counts):
    c = np.asarray(counts, float)
    c = c[c > 0]
    if c.size == 0:
        return float('nan')
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def miller_madow(counts):
    c = np.asarray(counts, float)
    n, k = c.sum(), (c > 0).sum()
    if n == 0:
        return float('nan')
    return shannon(c) + (k - 1) / (2 * n * np.log(2))


def rarefied(counts, m, reps=50, seed=0):
    """Mean Shannon entropy (bits) over `reps` subsamples of m items drawn without replacement; NaN if the counts hold fewer than m items."""
    c = np.asarray(counts, int)
    if c.sum() < m or m <= 0:
        return float('nan')
    rng = np.random.default_rng(seed)
    labels = np.repeat(np.arange(len(c)), c)
    vals = []
    for _ in range(reps):
        pick = rng.choice(labels, m, replace=False)
        vals.append(shannon(np.bincount(pick, minlength=len(c))))
    return float(np.mean(vals))


def cluster_bootstrap(values, clusters, stat, reps=1000, seed=0):
    """(estimate, low, high): stat(values) on all rows and the 2.5 / 97.5 percentiles over bootstrap resamples of whole clusters."""
    values = np.asarray(values, float)
    clusters = np.asarray(clusters)
    uniq, inv = np.unique(clusters, return_inverse=True)
    groups = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    est = stat(values)
    boots = []
    for _ in range(reps):
        pick = rng.integers(0, len(groups), len(groups))
        boots.append(stat(values[np.concatenate([groups[i] for i in pick])]))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return float(est), float(lo), float(hi)


def diff_ci(values, clusters, post, reps=1000, seed=0):
    """Mean(values | post) - mean(values | not post) with a cluster bootstrap interval. `post`: boolean per row."""
    values = np.asarray(values, float); post = np.asarray(post, bool); clusters = np.asarray(clusters)
    ok = ~np.isnan(values)
    values, post, clusters = values[ok], post[ok], clusters[ok]
    uniq, inv = np.unique(clusters, return_inverse=True)
    n = len(uniq)
    s1 = np.bincount(inv, weights=values * post, minlength=n); c1 = np.bincount(inv, weights=post.astype(float), minlength=n)
    s0 = np.bincount(inv, weights=values * ~post, minlength=n); c0 = np.bincount(inv, weights=(~post).astype(float), minlength=n)

    def d(w):
        a, b = (w * c1).sum(), (w * c0).sum()
        return (w * s1).sum() / a - (w * s0).sum() / b if a > 0 and b > 0 else float('nan')
    est = d(np.ones(n))
    rng = np.random.default_rng(seed)
    boots = [d(np.bincount(rng.integers(0, n, n), minlength=n).astype(float)) for _ in range(reps)]
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return float(est), float(lo), float(hi), int(n)


def mean_by_year(values, years, clusters, reps=500, seed=0):
    """{year: (mean, low, high, n)} with a cluster bootstrap (one resample of the clusters is shared by all years)."""
    values = np.asarray(values, float); years = np.asarray(years); clusters = np.asarray(clusters)
    ok = ~np.isnan(values)
    values, years, clusters = values[ok], years[ok], clusters[ok]
    uniq, inv = np.unique(clusters, return_inverse=True)
    ys = np.unique(years)
    n = len(uniq)
    S = np.stack([np.bincount(inv, weights=values * (years == y), minlength=n) for y in ys])
    N = np.stack([np.bincount(inv, weights=(years == y).astype(float), minlength=n) for y in ys])
    rng = np.random.default_rng(seed)
    W = np.stack([np.bincount(rng.integers(0, n, n), minlength=n) for _ in range(reps)]).astype(float)
    boots = (W @ S.T) / np.maximum(W @ N.T, 1e-9)
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    return {int(y): (float(S[i].sum() / N[i].sum()), float(lo[i]), float(hi[i]), int(N[i].sum())) for i, y in enumerate(ys)}


def entropy_bootstrap(labels, clusters, m, reps=100, seed=0):
    """(estimate, low, high) of the entropy (bits) of `labels` rarefied to m items: the estimate averages 20 subsamples of the data, the
    interval is the 2.5 / 97.5 percentiles of one rarefied entropy per bootstrap resample of whole clusters. NaN when fewer than m items."""
    labels = np.asarray(labels); clusters = np.asarray(clusters)
    if len(labels) < m:
        return float('nan'), float('nan'), float('nan')
    _, lab = np.unique(labels, return_inverse=True)
    k = lab.max() + 1
    est = rarefied(np.bincount(lab, minlength=k), m, reps=20, seed=seed)
    uniq, inv = np.unique(clusters, return_inverse=True)
    groups = [np.nonzero(inv == i)[0] for i in range(len(uniq))]
    rng = np.random.default_rng(seed + 1)
    vals = []
    for _ in range(reps):
        rows = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        vals.append(rarefied(np.bincount(lab[rows], minlength=k), m, reps=1, seed=int(rng.integers(1 << 30))))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return est, float(lo), float(hi)
