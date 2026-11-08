"""Lab-cluster bootstrap on lab x year sufficient statistics (numpy only).

Every measure is a ratio of sums, M_t = sum_l w_l S[l,t] / sum_l w_l N[l,t], where l is a lab and w_l a bootstrap weight (the number of
times the lab is drawn; row 0 of W is all ones = the point estimate). Resampling is stratified by school so the school mix is fixed.
A paper of two labs counts in both (the strict membership); intervals are 2.5/97.5 percentiles of B draws.
"""
import numpy as np
import pandas as pd

PRE = list(range(2016, 2023))      # ChatGPT launched 2022-11-30; 2022 is in the pre period (sensitivity: dropped)
POST = [2023, 2024, 2025]
YEARS = list(range(2016, 2026))
CONTRASTS = {
    'post_minus_pre': (POST, PRE),
    'post_minus_pre_excl2022': (POST, [y for y in PRE if y != 2022]),
    'placebo_2019_21_minus_2016_18': ([2019, 2020, 2021], [2016, 2017, 2018]),
    'placebo_2020_21_minus_2016_19': ([2020, 2021], [2016, 2017, 2018, 2019]),
}


def weights(strata, B, seed):
    """(B+1, L) bootstrap counts; row 0 = ones. strata: array of stratum labels per lab."""
    rng = np.random.default_rng(seed)
    strata = np.asarray(strata)
    W = np.ones((B + 1, len(strata)))
    for s in np.unique(strata):
        ix = np.where(strata == s)[0]
        d = rng.integers(0, len(ix), (B, len(ix)))
        W[1:, ix] = np.apply_along_axis(lambda r: np.bincount(r, minlength=len(ix)), 1, d)
    return W


def lab_year(df, lab, year, num, den=None, labs=None):
    """S, N matrices (labs x YEARS) summing `num` and `den` (default 1 per row) by lab and year."""
    labs = labs if labs is not None else np.sort(df[lab].unique())
    li = pd.Series(np.arange(len(labs)), index=labs)
    d = df[df[year].between(YEARS[0], YEARS[-1]) & df[lab].isin(labs)]
    r = li.loc[d[lab]].to_numpy()
    c = d[year].to_numpy().astype(int) - YEARS[0]
    S = np.zeros((len(labs), len(YEARS)))
    N = np.zeros_like(S)
    np.add.at(S, (r, c), d[num].to_numpy(float))
    np.add.at(N, (r, c), 1.0 if den is None else d[den].to_numpy(float))
    return S, N, labs


def series(S, N, W):
    """(B+1, T) yearly ratio for every bootstrap row."""
    with np.errstate(invalid='ignore', divide='ignore'):
        return (W @ S) / (W @ N)


def pooled(S, N, W, years):
    idx = [y - YEARS[0] for y in years]
    with np.errstate(invalid='ignore', divide='ignore'):
        return (W @ S[:, idx].sum(1)) / (W @ N[:, idx].sum(1))


def ci(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return (np.nan, np.nan) if len(a) < 30 else (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))


def describe(M):
    """M: (B+1, ...) -> est, lo, hi along axis 0."""
    est = M[0]
    lo = np.nanpercentile(M[1:], 2.5, axis=0)
    hi = np.nanpercentile(M[1:], 97.5, axis=0)
    return est, lo, hi


def tables(meta, S, N, W, transform=None, contrasts=CONTRASTS):
    """Yearly series and contrasts of a ratio measure as two long DataFrames (meta: dict of identifying columns)."""
    tf = transform or (lambda x: x)
    M = tf(series(S, N, W))
    est, lo, hi = describe(M)
    ser = pd.DataFrame(dict(meta, year=YEARS, est=est, lo=lo, hi=hi, n=N.sum(0)))
    rows = []
    for name, (post, pre) in contrasts.items():
        d = tf(pooled(S, N, W, post)) - tf(pooled(S, N, W, pre))
        e = float(d[0])
        lo_, hi_ = ci(d[1:])
        rows.append(dict(meta, contrast=name, est=e, lo=lo_, hi=hi_, pre=float(tf(pooled(S, N, W, pre))[0]), post=float(tf(pooled(S, N, W, post))[0])))
    return ser, pd.DataFrame(rows)
