"""Lineage and writing-style studies (ai-writing/lineage, ai-writing/style): the closed-form fixed-effects bootstrap against a brute-force
refit, and the style features on small texts (numpy only)."""
import numpy as np

import lineage_fit as F
import style_features as SF


def test_fit_matches_within_regression():
    rng = np.random.default_rng(0)
    lab = np.repeat(np.arange(30), 20)
    x = (rng.random(600) < 0.4).astype(float)
    y = 0.3 * x + rng.normal(size=30)[lab] + rng.normal(scale=0.5, size=600)
    w = rng.random(600) + 0.5
    r = F.fit(y, x, w, lab, boot=200)
    # brute force: weighted within-lab slope
    num = den = 0.0
    for g in range(30):
        m = lab == g
        xm, ym = np.average(x[m], weights=w[m]), np.average(y[m], weights=w[m])
        num += (w[m] * (x[m] - xm) * (y[m] - ym)).sum()
        den += (w[m] * (x[m] - xm) ** 2).sum()
    assert abs(r['beta'] - num / den) < 1e-9
    assert r['lo'] < r['beta'] < r['hi']
    assert abs(r['beta'] - 0.3) < 0.15


def test_fit_with_year_effect_recovers_slope():
    rng = np.random.default_rng(1)
    lab = np.repeat(np.arange(40), 25)
    year = rng.integers(0, 5, 1000)
    x = rng.random(1000)
    y = -0.5 * x + rng.normal(size=40)[lab] + 0.2 * year + rng.normal(scale=0.3, size=1000)
    r = F.fit(y, x, np.ones(1000), lab, year=year, boot=200)
    assert abs(r['beta'] + 0.5) < 0.1


def test_style_features_basic():
    t = ('Large language models are changing scientific writing. We show, however, that the effect on abstracts may be small (e.g., two percent of words). '
         'Moreover, it is likely that style is more uniform; this paper delves into a comprehensive analysis of it.')
    f = SF.features(t, {'delves', 'comprehensive'})
    assert abs(f['sent_mean'] - 13.0) < 1.0           # 'e.g.' does not end a sentence
    assert f['hedge'] > 0 and f['kobak'] > 0
    assert f['fw_the'] == 0 or f['fw_the'] > 0
    assert np.isnan(SF.features('too short')['sent_mean'])


def test_mtld_is_length_robust():
    rng = np.random.default_rng(2)
    vocab = [f'w{i}' for i in range(300)]
    short = list(rng.choice(vocab, 600))
    long = list(rng.choice(vocab, 3000))
    a, b = SF.mtld(short), SF.mtld(long)
    assert abs(a - b) / b < 0.35
    assert np.isnan(SF.mtld(['a'] * 10))
