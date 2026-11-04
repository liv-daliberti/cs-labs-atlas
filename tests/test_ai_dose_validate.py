"""Detector validation tables (ai-writing/dose/dose_validate.py) on synthetic scored papers: FPR per group, recalibration, panels."""
# ruff: noqa: E402
import pytest

pytest.importorskip('pandas')

import numpy as np
import pandas as pd

import dose_build as B
import dose_validate as V


def papers(rng, n=600):
    rows, ps = [], []
    for i in range(n):
        school = 'mit' if i % 2 else 'stanford'
        n_p = int(rng.integers(20, 40))
        # stanford passages are scored higher by the detector (a domain shift): its false-positive rate is ~4%, mit's ~1%
        p = np.where(rng.random(n_p) < (0.04 if school == 'stanford' else 0.01), 0.2 + 0.79 * rng.random(n_p), 1e-5 * (1 + rng.random(n_p)))
        rows.append(dict(paper_id=f'p{i}', year=2018, home_school=school, schools=[school], trained_on=False, field_grp='Computer Science', oa_field='Computer Science'))
        ps += [(f'p{i}', j, 150, float(v)) for j, v in enumerate(p)]
    return pd.DataFrame(rows), pd.DataFrame(ps, columns=['paper_id', 'pidx', 'words', 'p'])


def scored(df, ps, thr=1e-3):
    d = B.paper_dose(ps, thr)
    return df.merge(d, on='paper_id')


def test_paper_dose_definitions():
    ps = pd.DataFrame(dict(paper_id=['a'] * 4 + ['b'] * 2, pidx=[0, 1, 2, 3, 0, 1], words=150, p=[.9, .1, .0, .6, .0, .0]))
    d = B.paper_dose(ps, 0.5).set_index('paper_id')
    assert d.loc['a', 'ai_share'] == 0.5 and d.loc['a', 'ai_any'] == 1 and d.loc['b', 'ai_any'] == 0 and abs(d.loc['a', 'mean_p_par'] - 0.4) < 1e-9


def test_pre_table_flags_the_shifted_school_and_recalibration_fixes_it():
    rng = np.random.default_rng(0)
    df, ps = papers(rng)
    df = scored(df, ps)
    t = V.pre_table(df, 'school', 'all').set_index('school')
    assert t.loc['stanford', 'well_above'] and not t.loc['mit', 'well_above']
    thr = V.group_thresholds(df.assign(trained_on=False), ps, ['stanford'], [])
    assert thr[('school', 'stanford')] > 0.2
    cal = V.recalibrated_share(df, ps, thr)
    assert cal[df['home_school'] == 'stanford'].mean() < 0.02          # back near the 1% design rate


def test_explode_and_field_groups():
    df = pd.DataFrame(dict(paper_id=list('abc'), year=2018, schools=[['mit', 'cmu'], ['mit'], ['xx']], oa_field=['A', 'B', None], ai_share=[0., 0., 0.]))
    e = V.explode_schools(df)
    assert len(e) == 3                      # 'xx' is not a study school
    assert set(V.field_groups(df, min_n=2)) == {'Other', 'Unknown'}


def test_cross_check_panel_correlations():
    rows = [dict(school=s, year=y, flagged=0.01 + 0.02 * (y - 2016) * (1 + 0.1 * i), mean_ai_share=0.01 * (y - 2016), abs_flagged=0.02 * (y - 2016), kobak_abs=40 + 3 * (y - 2016), kobak_ft=0)
            for i, s in enumerate(['mit', 'cmu']) for y in range(2016, 2027)]
    liang = pd.DataFrame([dict(school=s, year=y, alpha=0.03 * (y - 2016), n=500) for s in ['mit', 'cmu'] for y in range(2016, 2027)])
    panel, corr, within = V.cross_check(pd.DataFrame(rows), liang)
    assert corr.loc['flagged', 'liang_alpha'] > 0.95 and within.loc['kobak_abs', 'liang_alpha'] > 0.95


def test_precision_compare():
    import check_precision as C
    old = np.array([1e-6, 1e-3, 0.5, 0.9, 1e-9])
    assert C.compare(old, old, 1e-3)['flag_change'] == 0 and C.compare(old, old * 1.0001, 1e-3)['logit_corr'] > 0.9999
    assert C.compare(old, np.array([1e-6, 1e-4, 0.5, 0.9, 1e-9]), 1e-3)['flag_change'] == 0.2
