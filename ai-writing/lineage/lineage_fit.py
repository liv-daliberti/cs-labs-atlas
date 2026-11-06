"""Weighted fixed-effects estimates with a cluster bootstrap over labs, in closed form (no refitting per draw).

fit(y, x, w, lab, year=None): beta of y on x after removing lab (and year) fixed effects, weights w. Each lab's contribution
(Sxx_l, Sxy_l) is computed once; a bootstrap draw reweights labs by multinomial counts, so beta_b = (c.Sxy)/(c.Sxx).
With a year effect the residuals are computed once on the full sample (Frisch-Waugh), the draws reweight them: a close
approximation, noted in the report.
"""
import numpy as np

B = 1000


def _resid(v, w, lab, year, iters=12):
    v = v.astype(float).copy()
    for _ in range(iters if year is not None else 1):
        for g in ([lab, year] if year is not None else [lab]):
            sw = np.bincount(g, w)
            m = np.bincount(g, w * v) / np.clip(sw, 1e-12, None)
            v = v - m[g]
    return v


def fit(y, x, w, lab, year=None, seed=0, boot=B):
    y, x, w = (np.asarray(a, float) for a in (y, x, w))
    lab = np.unique(lab, return_inverse=True)[1]
    yr = None if year is None else np.unique(year, return_inverse=True)[1]
    xr, yres = _resid(x, w, lab, yr), _resid(y, w, lab, yr)
    sxx = np.bincount(lab, w * xr * xr)
    sxy = np.bincount(lab, w * xr * yres)
    if sxx.sum() <= 1e-12:
        return dict(beta=np.nan, lo=np.nan, hi=np.nan, n_labs=0)
    beta = sxy.sum() / sxx.sum()
    rng = np.random.default_rng(seed)
    G = len(sxx)
    use = np.flatnonzero(sxx > 1e-12)
    bs = []
    for _ in range(boot // 50):
        c = rng.multinomial(G, np.full(G, 1.0 / G), size=50).astype(float)[:, use]
        den = c @ sxx[use]
        bs.append((c @ sxy[use]) / np.where(den > 0, den, np.nan))
    bs = np.concatenate(bs)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return dict(beta=float(beta), lo=float(lo), hi=float(hi), n_labs=int(len(use)))
