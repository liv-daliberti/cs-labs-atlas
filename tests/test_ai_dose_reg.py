"""Fixed-effects regression of the AI-dose study against synthetic data with known coefficients."""
import numpy as np
import pandas as pd

import dose_reg as R


def frame(seed=0, n_lab=80, per=12, beta=0.30):
    rng = np.random.default_rng(seed)
    lab = np.repeat(np.arange(n_lab), per)
    year = rng.integers(2023, 2027, n_lab * per)
    lab_eff = rng.normal(0, 1, n_lab)[lab]
    yr_eff = np.array([0, .2, .5, .9])[year - 2023]
    x = np.clip(rng.beta(1, 4, n_lab * per) + 0.3 * lab_eff, 0, None)     # dose is confounded with the lab
    ctrl = rng.normal(size=n_lab * per)
    y = beta * x + lab_eff * 2 + yr_eff + 0.5 * ctrl + rng.normal(0, 0.3, n_lab * per)
    return pd.DataFrame(dict(y=y, x=x, lab=lab, year=year, ctrl=ctrl, venue=rng.choice(['a', 'b', 'c'], n_lab * per)))


def test_pooled_is_biased_but_fixed_effects_recover_the_slope():
    d = frame()
    pooled = R.fit(d, 'y', 'x', controls=['ctrl'], fe=['year'], cluster='lab')
    fe = R.fit(d, 'y', 'x', controls=['ctrl'], fe=['year', 'lab'], cluster='lab')
    assert pooled['beta'] > 0.8                      # lab effect leaks into the pooled slope
    assert abs(fe['beta'] - 0.30) < 0.08 and fe['lo'] < 0.30 < fe['hi']
    assert fe['clusters'] == 80 and abs(fe['coefs']['ctrl'] - 0.5) < 0.05


def test_categorical_controls_and_weights():
    d = frame(1)
    r = R.fit(d, 'y', 'x', controls=['ctrl', 'venue'], fe=['year', 'lab'], cluster='lab', weights=None)
    d['w'] = 1.0
    r2 = R.fit(d, 'y', 'x', controls=['ctrl', 'venue'], fe=['year', 'lab'], cluster='lab', weights='w')
    assert abs(r['beta'] - r2['beta']) < 1e-6 and 'venue_b' in r['coefs']


def test_absorb_two_way_matches_dummy_regression():
    rng = np.random.default_rng(2)
    a, b = rng.integers(0, 6, 400), rng.integers(0, 5, 400)
    x = rng.normal(size=400) + 0.5 * a
    y = 2 * x + a + 3 * b + rng.normal(size=400)
    M = R.absorb(np.column_stack([y, x]), [a, b])
    beta = (M[:, 1] @ M[:, 0]) / (M[:, 1] @ M[:, 1])
    D = np.column_stack([x, np.eye(6)[a], np.eye(5)[b][:, 1:]])
    assert abs(beta - np.linalg.lstsq(D, y, rcond=None)[0][0]) < 1e-6


def test_degenerate_input_returns_nan():
    d = pd.DataFrame(dict(y=np.arange(20.), x=np.ones(20)))
    assert np.isnan(R.fit(d, 'y', 'x')['beta'])
