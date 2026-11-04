"""Site histograms (dose_site.py): the browser-side computation from 101-bin histograms must equal the direct per-paper calculation at several cutoffs."""
# ruff: noqa: E402
import pytest

pytest.importorskip('pandas')

import numpy as np
import pandas as pd

import dose_site as S


def doses(seed=0, n=3000):
    rng = np.random.default_rng(seed)
    x = np.where(rng.random(n) < 0.6, 0.0, rng.beta(1, 3, n))
    x[:40] = np.round(np.linspace(0, 1, 40), 2)               # exact edges: 0.25, 0.5 ... must land in their own bin
    return x


def test_bin_rule_edges():
    assert S.dose_bin([0.0, 0.0099, 0.01, 0.25, 0.5, 0.99, 1.0, np.nan]).tolist() == [0, 0, 1, 25, 50, 99, 100, -1]
    assert S.dose_bin([2 / 8 * 100 / 100]).tolist() == [25]
    assert S.dose_bin([0.07 + 0.01 * 0]).tolist() == [7]


@pytest.mark.parametrize('t', [1, 5, 10, 25, 33, 50, 75, 100])
def test_histogram_reproduces_direct_calculation(t):
    x = doses()
    c, s = S.hist(x)
    n, share, mean, median = S.at_cutoff(c, s, t)
    sel = x[x >= t / 100 - 1e-12]
    assert n == len(sel) and abs(share - len(sel) / len(x)) < 1e-12
    if len(sel):
        assert abs(mean - sel.mean()) < 0.006 and abs(median - np.median(sel)) < 0.011   # the median is read at bin resolution


def test_empty_cutoff_and_histograms_of_a_frame():
    c, s = S.hist([0.0, 0.0])
    n, share, mean, median = S.at_cutoff(c, s, 25)
    assert n == 0 and share == 0.0 and np.isnan(mean) and np.isnan(median)
    rng = np.random.default_rng(1)
    rows = [dict(paper_id=f'p{i}', year=2024, schools=['mit'], ai_share=(v if i % 4 else np.nan), ai_share_cal=np.nan, p_ai_abstract=0.5, flag_abstract=float(i % 8 == 0),
                 trained_on=False, lab0=f'l{i % 7}') for i, v in enumerate(rng.random(400))]
    h = S.histograms(pd.DataFrame(rows), bands=True)
    cell = h['mit']['2024']
    assert cell['n_ft'] == 300 and sum(cell['hist']) == 300 and cell['abstract_only']['n'] == 100 and cell['abstract_only']['flagged'] == 50
    assert set(cell['band']) == {str(t) for t in S.CI_T} and cell['band']['25'][0] <= cell['band']['25'][1]
    assert h['all']['2024']['n_ft'] == 300


def test_lab_sparse_histogram_and_position():
    df = pd.DataFrame(dict(paper_id=[f'p{i}' for i in range(12)], year=2024, ai_share=[0.0] * 6 + [0.5] * 6, ai_share_cal=np.nan, schools=[['mit']] * 12))
    lp = pd.DataFrame(dict(paper_id=df['paper_id'], lab_id=['a'] * 6 + ['b'] * 3 + ['c'] * 3, school='mit', lab_name='x', pi='y'))
    r = S.lab_hists(df, lp)['mit']
    assert [x['lab_id'] for x in r] == ['a', 'b'][:1] or len(r) == 1
    assert r[0]['bins'] == [0] and r[0]['counts'] == [6]
    ps = pd.DataFrame(dict(paper_id=['p6'] * 10, pidx=range(10), words=150, p=[0.9] + [0.0] * 9))
    cuts = pd.Series(1e-3, index=df['paper_id'])
    out = S.position(df, ps, cuts)['all']['post']
    assert out['total'][50][0] == 1 and out['flagged'][50][0] == 1 and sum(map(sum, out['flagged'])) == 1
