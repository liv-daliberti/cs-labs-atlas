"""Non-text sameness measures (ai-writing/study/sameness_*): null shuffle, histogram statistics, dictionary matcher, contrasts, verdict rule."""
import numpy as np
import pytest

pytest.importorskip('pandas')
sp = pytest.importorskip('scipy.sparse')
import sameness_common as SC  # noqa: E402
import sameness_dictionary as D  # noqa: E402
import sameness_refs as R  # noqa: E402
import sameness_report as RP  # noqa: E402
import sameness_topics as TP  # noqa: E402


def test_null_keeps_list_sizes_and_totals():
    rng = np.random.default_rng(0)
    B = sp.csr_matrix((rng.random((30, 400)) < 0.05).astype(float))
    Bn = R.null_matrix(B, rng)
    assert Bn.shape == B.shape
    a, an = np.asarray(B.sum(1)).ravel(), np.asarray(Bn.sum(1)).ravel()
    assert (an <= a).all() and an.sum() >= 0.9 * a.sum()
    assert set(Bn.data) == {1.0}


def test_null_removes_structure():
    n, per = 40, 60                                  # two blocks of labs citing disjoint pools: observed overlap is high, null overlap is near the pooled rate
    rows = []
    for i in range(n):
        pool = np.arange(0, 500) if i < n // 2 else np.arange(500, 1000)
        rows.append(np.random.default_rng(i).choice(pool, per, replace=False))
    B = sp.csr_matrix((np.ones(n * per), np.concatenate(rows), np.arange(0, n * per + 1, per)), shape=(n, 1000))
    I, a = R.pair_stats(B)
    j, _ = R.jac_cos(I, a)
    jn, _ = R.jac_cos(*R.pair_stats(R.null_matrix(B, np.random.default_rng(1))))
    same = np.arange(n)[:, None] // (n // 2) == np.arange(n)[None, :] // (n // 2)
    off = ~np.eye(n, dtype=bool)
    assert j[same & off].mean() > 1.5 * jn[same & off].mean()


def test_hist_stats_equal_counts_and_one_dominant():
    h = np.zeros(11)
    h[5] = 200                                       # 200 works cited 5 times each
    s = R.hist_stats(h)
    assert abs(s['gini']) < 1e-9 and abs(s['hhi'] - 1 / 200) < 1e-9 and abs(s['top1pct'] - 0.01) < 1e-9
    h2 = np.zeros(1001)
    h2[1] = 199
    h2[1000] = 1
    s2 = R.hist_stats(h2)
    assert s2['gini'] > 0.8 and s2['top1pct'] > 0.8


def test_matcher_case_plural_and_family():
    m = D.Matcher()
    names = lambda t: {m.names[i] for i in m.counts(t)}  # noqa: E731
    assert names('Trained on CIFAR-10 and ImageNet.') >= {'CIFAR', 'ImageNet'}
    assert 'Transformer' in names('Transformers are used.')
    assert 'CLIP' not in names('a clip of video')            # case-sensitive entry
    assert 'Neural scaling laws' not in names('scaling laws for the energetics of flapping')
    assert 'Chain of thought' in names('with chain-of-thought prompting')


def test_contrast_rows_recovers_step_and_placebo():
    rng = np.random.default_rng(0)
    V = rng.normal(0, 0.01, (101, 10))
    V[:, 7:] += 1.0
    ser, con = SC.contrast_rows({'m': 'x'}, V)
    c = con.set_index('contrast')
    assert 0.95 < c.loc['post_minus_pre', 'est'] < 1.05 and c.loc['post_minus_pre', 'lo'] > 0.9
    assert abs(c.loc['placebo_2019_21_minus_2016_18', 'est']) < 0.05


def test_verdict_direction_and_drift():
    import pandas as pd
    post = pd.Series(dict(direction=-1, est=-0.011, lo=-0.016, hi=-0.006))
    assert RP.verdict(post, None) == 'toward sameness'
    plc = pd.Series(dict(est=-0.02, lo=-0.03, hi=-0.01))
    assert 'continues' in RP.verdict(post, plc)
    assert RP.verdict(pd.Series(dict(direction=1, est=0.01, lo=-0.01, hi=0.03)), None) == 'no change detectable'


def test_jsd_matrix_identical_and_disjoint():
    P = np.array([[1.0, 0, 0], [1.0, 0, 0], [0, 1.0, 0]])
    D_ = TP.jsd_matrix(P)
    assert abs(D_[0, 1]) < 1e-12 and abs(D_[0, 2] - 1.0) < 1e-9


def test_interval_recentres_on_the_estimate():
    rng = np.random.default_rng(1)
    draws = rng.normal(5.0, 1.0, 2000)                # draws biased up by 5 relative to the estimate 0
    lo, hi = SC.interval(draws, 0.0, center=True)
    assert lo < 0 < hi and abs((lo + hi) / 2) < 0.2
    lo2, hi2 = SC.interval(draws, 0.0, center=False)
    assert lo2 > 0
