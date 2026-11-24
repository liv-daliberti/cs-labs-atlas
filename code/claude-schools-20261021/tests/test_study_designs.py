"""The three design layers of the 12-school study (ai-writing/study/study_fe.py, study_design_*.py): the within estimator and the designs recover planted effects (numpy/pandas only)."""
import numpy as np
import pytest

pytest.importorskip('pandas')
import pandas as pd  # noqa: E402
import study_design_exposure as DX  # noqa: E402
import study_design_panel as DP  # noqa: E402
import study_design_revision as DR  # noqa: E402
import study_fe as FE  # noqa: E402


def make_panel(n_pi=400, per=6, seed=0, post_effect=0.15, drift=0.0, slope_sd=0.0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_pi):
        a = rng.normal(0, 0.5)
        sl = rng.normal(drift, slope_sd)
        for y in range(2016, 2026):
            for _ in range(per):
                v = a + sl * (y - 2022) + (post_effect if y >= 2023 else 0.0) + rng.normal(0, 0.3)
                rows.append((f's|p{i}', 's' if i % 2 else 'cmu', y, v))
    return pd.DataFrame(rows, columns=['pi_key', 'school', 'year', 'y'])


def test_within_removes_group_mean_and_trend():
    rng = np.random.default_rng(1)
    codes = np.repeat(np.arange(50), 8)
    t = np.tile(np.arange(8), 50).astype(float)
    y = 3.0 * codes + (0.5 + 0.1 * codes) * t
    r = FE.within(y, codes, None, t)
    assert np.abs(r).max() < 1e-8
    r0 = FE.within(y + rng.normal(0, 1, len(y)), codes)
    assert abs(np.bincount(codes, weights=r0[:, 0])).max() < 1e-8


def test_fit_recovers_coefficient_and_interval_covers():
    rng = np.random.default_rng(2)
    codes = np.repeat(np.arange(300), 10)
    x = rng.normal(size=len(codes))
    y = 2.0 * codes % 7 + 0.4 * x + rng.normal(0, 1, len(codes))
    r = FE.fit(y, x[:, None], codes, codes, names=['x'])
    t = FE.table(r)[0]
    assert t['lo'] < 0.4 < t['hi'] and t['hi'] - t['lo'] < 0.2


def test_panel_post_effect_with_pi_trends_and_common_drift():
    # a common upward calendar drift of 0.05 per year inflates the naive within-PI change; the PI-specific trend takes it out
    d = make_panel(post_effect=0.15, drift=0.05, slope_sd=0.02)
    rows, ev = DP.fit_specs(d, 'y', 2023)
    est = {r['spec']: r for r in rows}
    assert est['S0_pi_fe']['est'] > 0.35                       # drift + effect, mixed
    assert est['S2_pi_trend']['term'] == 'post_avg' and est['S2_pi_trend']['lo'] < 0.15 < est['S2_pi_trend']['hi']
    assert any(e['spec'] == 'S3_event' and e['term'] == 'y2016' for e in ev)
    wald = [e for e in ev if e['term'] == 'pretrend_wald'][0]
    assert wald['p'] < 0.01                                    # the drift is visible as a pre-trend


def test_panel_placebo_break_is_null_without_effect():
    d = make_panel(post_effect=0.0, drift=0.0)
    d = d[d.year <= 2021]
    rows, _ = DP.fit_specs(d, 'y', 2020)
    s2 = [r for r in rows if r['spec'] == 'S2_pi_trend'][0]
    assert s2['lo'] < 0 < s2['hi']


def test_ramping_effect_is_not_absorbed_by_the_trend():
    # an effect that ramps 0.1, 0.2, 0.3 over the post years: the per-year post dummies keep the pre-only trend, so the average departure is 0.2
    d = make_panel(post_effect=0.0, drift=0.0)
    d['y'] = d['y'] + np.select([d.year == 2023, d.year == 2024, d.year == 2025], [0.1, 0.2, 0.3], 0.0)
    rows, _ = DP.fit_specs(d, 'y', 2023, events=False)
    s2 = [r for r in rows if r['spec'] == 'S2_pi_trend'][0]
    assert s2['lo'] < 0.2 < s2['hi']


def test_balanced_samples():
    d = make_panel(n_pi=30, per=1)
    d = d[~((d.pi_key == 's|p0') & (d.year >= 2023))]
    m = DP.samples(d, 2023)
    assert not m['balanced1'][d.pi_key == 's|p0'].any() and m['balanced1'][d.pi_key == 's|p1'].all()
    assert m['balanced3'].sum() == 0 or m['balanced3'].sum() <= len(d)


def test_exposure_did_recovers_interaction_and_flags_pretrend():
    rng = np.random.default_rng(3)
    n = 500
    e = rng.normal(size=n)
    rows = []
    for i in range(n):
        a = rng.normal(0, 0.4)
        for y in range(2016, 2026):
            for _ in range(5):
                rows.append((f's|p{i}', 'a' if i % 2 else 'b', y, e[i], a + (0.1 * e[i] if y >= 2023 else 0) + rng.normal(0, 0.3)))
    d = pd.DataFrame(rows, columns=['pi_key', 'school', 'year', 'E', 'y'])
    res = DX.did(d, 'y', 'E', brk=2023)
    assert res['did']['lo'] < 0.1 < res['did']['hi']
    ev = res['event']
    assert abs(ev[ev.year == 2025]['est'].iloc[0] - 0.1) < 0.05
    assert res['pretrend_p'] > 0.01


def test_revision_cells_and_effect():
    rng = np.random.default_rng(4)
    n = 600
    p = pd.DataFrame({'arxiv_id': [f'a{i}' for i in range(n)], 'lab0': [f'l{i % 60}' for i in range(n)], 'school': ['mit'] * n,
                      'cell': rng.choice(['pre_pre', 'pre_post', 'post_post'], n), 'v1': rng.normal(0.02, 0.01, n)})
    p['final'] = p['v1'] + np.where(p['cell'] == 'post_post', 0.08, 0.0) + rng.normal(0, 0.02, n)
    p['delta'] = p['final'] - p['v1']
    out = DR.cell_effects(p, 'delta', cluster='lab0', B=200, seed=1)
    pp = out[out.contrast == 'post_post - pre_pre'].iloc[0]
    assert pp.lo < 0.08 < pp.hi
    pr = out[out.contrast == 'pre_post - pre_pre'].iloc[0]
    assert pr.lo < 0 < pr.hi


def test_run_study_designs_array_matches_the_scan_tasks():
    import re
    from pathlib import Path

    import study_design_prep as PR
    sh = (Path(__file__).resolve().parents[1] / 'ai-writing' / 'study' / 'run_study.sh').read_text()
    assert int(re.search(r'^\s+n=(\d+)\s', sh, re.M).group(1)) == len(PR.tasks())


def test_language_exposure_is_an_institution_country_fact():
    import json

    import study_design_prep as PR
    ct = pd.DataFrame({'k': ['W1', 'W2'], 'authors': [json.dumps([['A1', ['US']], ['A2', ['CN']], ['A3', []], ['A4', ['IN', 'US']]]), json.dumps([['A5', ['DE']]])]})
    r = PR.paper_language(ct).set_index('k')
    assert r.loc['W1', 'n_authors'] == 4 and r.loc['W1', 'n_known'] == 3 and r.loc['W1', 'n_nonang'] == 1 and r.loc['W1', 'n_nonang_wide'] == 1
    assert r.loc['W2', 'n_nonang'] == 1
