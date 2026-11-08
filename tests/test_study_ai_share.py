"""The AI-share site file of the 12-school study (ai-writing/study/study_ai_share.py): shape, years, fractions (pandas)."""
import json

import pytest

pytest.importorskip('pandas')
import pandas as pd  # noqa: E402
import study_ai_share as S  # noqa: E402


def tables():
    rows = []
    for sc in ('ALL', 'cmu', 'harvard'):
        for m in S.MEASURES:
            for y in range(2016, 2027):
                rows.append(dict(measure=m, scope=sc, sample='all', n_labs=5, year=y, est=0.01 * (y - 2015), lo=0.0, hi=0.2, n=500 if sc != 'harvard' else 3))
    con = pd.DataFrame([dict(measure=m, scope=sc, sample='all', contrast=c, est=0.1, lo=0.05, hi=0.15, pre=0.0, post=0.1)
                        for sc in ('ALL', 'cmu') for m in S.MEASURES for c in ('post_minus_pre', 'placebo_2019_21_minus_2016_18')])
    fp = pd.DataFrame([dict(scope='ALL', year=y, observed=0.1, lo=0.09, hi=0.11, corrected=0.09, corrected_lo=0.08, corrected_hi=0.1, miss=ms, fpr='fpr')
                       for y in (2023, 2024, 2025) for ms in ('miss0', 'miss6.6')])
    cov = pd.DataFrame([dict(school=s, year=y, papers=10, scored=5, in_universe=9) for s in ('cmu', 'harvard') for y in range(2016, 2026)])
    return dict(ai_series=pd.DataFrame(rows), ai_contrasts=con, ai_fp_corrected=fp, ai_coverage=cov)


def test_build_shape_and_no_2026(tmp_path):
    snap = tmp_path
    (snap / 'ai').mkdir()
    (snap / 'ai' / 'v3_error_table.json').write_text(json.dumps({'operating_point': {}}))
    d = S.build(tables(), snap, '2026-11-07', 'snap')
    assert [r['year'] for r in d['series']['all']['heavy_main']] == list(range(2016, 2026))
    assert 'harvard' not in d['series']                      # fewer than 100 scored papers: not shown
    assert d['contrasts']['all']['heavy_main']['placebo_est'] == 0.1
    assert [r['year'] for r in d['corrected']] == [2023, 2024, 2025]
    assert any(c['school'] == 'harvard' and c['partial'] for c in d['coverage'])
    assert max(y for y in [r['year'] for m in d['series']['all'].values() for r in m]) == 2025
    json.dumps(d)
