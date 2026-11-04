"""Lab-year diversity draws, lab exposure and the DiD / placebo / event-study tables on synthetic labs with a planted effect."""
import numpy as np
import pandas as pd

import dose_lab as L


def test_draw_metrics_order_clustered_vs_spread():
    rng = np.random.default_rng(0)
    d = 16
    tight = rng.normal(size=(1, d)) + 0.05 * rng.normal(size=(20, d))
    wide = rng.normal(size=(20, d))
    Z = np.vstack([tight, wide]); Z /= np.linalg.norm(Z, axis=1, keepdims=True)
    labels = np.r_[np.zeros(20, int), np.arange(20)]
    a = L.draw_metrics(Z, np.arange(20), 5, 30, rng, labels)
    b = L.draw_metrics(Z, np.arange(20, 40), 5, 30, rng, labels)
    assert a['mpd'] < b['mpd'] and a['vendi'] < b['vendi'] and a['h_labels'] == 0 and b['h_labels'] > 2.0
    assert 1.0 <= a['vendi'] <= 5.0 and 1.0 <= b['vendi'] <= 5.0 + 1e-9


def test_lab_exposure_needs_min_scored():
    pl = pd.DataFrame(dict(lab_id=['a'] * 5 + ['b'] * 2, year=[2023, 2024, 2025, 2025, 2026, 2024, 2025], ai_share=[.1, .2, .3, .4, .5, .9, .9],
                           flag_abstract=[0, 1, 0, 1, 1, 1, 1]))
    t = L.lab_exposure(pl, min_scored=4).set_index('lab_id')
    assert abs(t.loc['a', 'dose'] - 0.3) < 1e-9 and np.isnan(t.loc['b', 'dose']) and abs(t.loc['a', 'abs_dose'] - 0.6) < 1e-9


def panel(effect, seed=0, n_lab=120):
    rng = np.random.default_rng(seed)
    rows = []
    for lab in range(n_lab):
        dose = rng.beta(1, 3)
        fe = rng.normal()
        for y in list(range(2017, 2022)) + list(range(2023, 2027)):
            rows.append(dict(lab_id=f'l{lab}', year=y, dose=dose, y=fe + 0.05 * (y - 2017) + effect * dose * (y >= 2023) + rng.normal(0, .2)))
    return pd.DataFrame(rows)


def test_did_recovers_effect_and_placebos_are_null():
    t = L.did_table(panel(-0.6), 'y', 'dose', boot=60)
    did = t[t['spec'] == 'did'].iloc[0]
    assert did['lo'] < -0.6 < did['hi']
    for b in L.BREAKS:
        p = t[t['spec'] == f'placebo{b}'].iloc[0]
        assert p['lo'] < 0 < p['hi']
    ev = t[t['spec'] == 'event'].set_index('year')
    assert ev.loc[2025, 'beta'] < -0.3 and abs(ev.loc[2018, 'beta']) < 0.3


def test_within_lab_year():
    p = panel(0.0)
    p['ai_share_lt'] = np.random.default_rng(1).random(len(p))
    p['y'] = p['y'] + 0.5 * p['ai_share_lt']
    r = L.within_lab_year(p, 'y', boot=60)
    assert r['lo'] < 0.5 < r['hi']
