"""Site data (dose_site.py): the AI flag definition, baseline adjustment and lab shrinkage on small fixtures."""
import numpy as np
import pandas as pd

import dose_site as S


def frame():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(2000):
        y = 2016 + i % 11
        share = (rng.random() < (0.01 if y < 2023 else 0.3)) * rng.uniform(0.25, 1) 
        rows.append(dict(paper_id=f'p{i}', year=y, schools=['mit'], ai_share=share, ai_share_cal=np.nan, flag_abstract=float(share > 0), trained_on=False))
    df = pd.DataFrame(rows)
    df.loc[df.index % 5 == 0, ['ai_share']] = np.nan     # no full text: falls back to the abstract flag
    return df


def test_primary_flag_falls_back_to_abstract():
    df = frame()
    prim, ft, ab = S.ai_flags(df)
    assert prim.notna().all() and ft.isna().sum() == (df['ai_share'].isna()).sum()
    assert (prim[df['ai_share'].isna()] == df.loc[df['ai_share'].isna(), 'flag_abstract']).all()


def test_how_much_baseline_adjustment():
    r = S.how_much(frame())
    rows = {x['year']: x for x in r['series']['primary']['all']}
    assert rows[2025]['adjusted'] > 0.2 and rows[2025]['adj_lo'] < rows[2025]['adjusted'] < rows[2025]['adj_hi']
    assert abs(rows[2018]['adjusted']) < 0.05 and rows[2026]['partial'] and not rows[2025]['partial']
    assert r['series']['primary']['mit'][0]['n'] > 0


def test_lab_shrinkage_and_minimum():
    df = pd.DataFrame(dict(paper_id=[f'p{i}' for i in range(12)], year=2024, ai_share=[1.0] * 6 + [0.0] * 6, ai_share_cal=np.nan))
    lp = pd.DataFrame(dict(paper_id=df['paper_id'], lab_id=['big'] * 6 + ['tiny'] * 6, school='mit', lab_name='x', pi='y'))
    lp = pd.concat([lp, lp.iloc[:0]])
    r = S.labs(df, lp)
    big = [x for x in r['rows'] if x['lab_id'] == 'big'][0]
    assert 0.5 < big['shrunk'] < big['mean'] and len(r['rows']) == 2
    r2 = S.labs(df.iloc[[0, 1, 6, 7]], lp[lp['paper_id'].isin(df['paper_id'].iloc[[0, 1, 6, 7]])])
    assert r2['rows'] == []
