"""Lab-cluster bootstrap of the 12-school study (ai-writing/study): weights, ratio series, contrasts (numpy/pandas only)."""
import numpy as np
import pytest

pytest.importorskip('pandas')
import study_labstats as L  # noqa: E402


def test_weights_stratified_and_point_row():
    W = L.weights(['a'] * 5 + ['b'] * 3, 20, 1)
    assert W.shape == (21, 8) and (W[0] == 1).all()
    assert (W[1:, :5].sum(1) == 5).all() and (W[1:, 5:].sum(1) == 3).all()


def test_series_and_contrast_recover_a_step():
    rng = np.random.default_rng(0)
    nl, T = 60, len(L.YEARS)
    N = rng.integers(5, 15, (nl, T)).astype(float)
    p = np.where(np.array(L.YEARS) >= 2023, 0.30, 0.05)
    S = rng.binomial(N.astype(int), p).astype(float)
    W = L.weights(['x'] * nl, 200, 3)
    ser, con = L.tables({'m': 'x'}, S, N, W)
    row = con[con.contrast == 'post_minus_pre'].iloc[0]
    assert 0.18 < row.est < 0.30 and row.lo < row.est < row.hi and row.lo > 0.1
    plc = con[con.contrast == 'placebo_2019_21_minus_2016_18'].iloc[0]
    assert plc.lo < 0 < plc.hi
    assert len(ser) == len(L.YEARS)


def test_lab_year_sums():
    import pandas as pd
    df = pd.DataFrame({'lab': ['a', 'a', 'b'], 'year': [2016, 2016, 2025], 'x': [1.0, 0.0, 1.0]})
    S, N, labs = L.lab_year(df, 'lab', 'year', 'x')
    assert list(labs) == ['a', 'b'] and S[0, 0] == 1 and N[0, 0] == 2 and N[1, -1] == 1
