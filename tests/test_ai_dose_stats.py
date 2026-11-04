"""AI-dose statistics (ai-writing/dose/dose_stats.py) on fixtures with known answers."""
import numpy as np
import pandas as pd

import dose_stats as S


def test_boot_ratio_covers_the_truth():
    rng = np.random.default_rng(0)
    n = rng.integers(20, 40, 400)
    f = rng.binomial(n, 0.05)
    est, lo, hi = S.boot_ratio(f, n, B=300)
    assert lo < 0.05 < hi and abs(est - f.sum() / n.sum()) < 1e-12
    est2, lo2, hi2 = S.boot_ratio(f, n, clusters=np.arange(400) // 20, B=300)
    assert est2 == est and (hi2 - lo2) > 0


def test_ols_cluster_matches_closed_form():
    rng = np.random.default_rng(1)
    g = np.repeat(np.arange(60), 10)
    x = rng.normal(size=600)
    y = 2.0 + 0.5 * x + rng.normal(size=60)[g] + rng.normal(size=600)
    X = np.column_stack([np.ones(600), x])
    b, se = S.ols_cluster(y, X, g)
    assert abs(b[1] - 0.5) < 0.15 and se[1] > 0
    est, lo, hi = S.cluster_boot_coef(y, X, g, 1, B=200)
    assert lo < 0.5 < hi


def test_demean_and_bins():
    df = pd.DataFrame(dict(g=[1, 1, 2, 2], x=[1., 3., 10., 14.]))
    assert S.demean(df, ['x'], ['g'])['x'].tolist() == [-1, 1, -2, 2]
    b = S.dose_bins([0, 0.04, 0.1, 0.3, 1.0])
    assert [str(v) for v in b] == ['0-5%', '0-5%', '5-25%', '25-50%', '50-100%']
