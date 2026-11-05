"""Owner rule 2026-11-04: 2026 is a partial year, so no site JSON, table or figure series holds it and post-period estimates end at 2025."""
# ruff: noqa: E402
import json
from pathlib import Path

import pytest

pytest.importorskip('pandas')

import numpy as np
import pandas as pd

import dcommon as D
import dose_lab as L
import dose_site as S
import dose_validate as V


def frame(n=600):
    rng = np.random.default_rng(0)
    rows = [dict(paper_id=f'p{i}', year=2016 + i % 11, schools=['mit'], home_school='mit', ai_share=rng.random(), ai_share_cal=np.nan, p_ai_abstract=0.5,
                 flag_abstract=float(i % 5 == 0), trained_on=False, lab0=f'l{i % 9}', kobak_abs=1.0, kobak_ft=1.0, n_passages=10, ai_any=1.0, mean_p_par=0.1, n_flagged=int(rng.integers(0, 4))) for i in range(n)]
    return pd.DataFrame(rows)


def test_constant_and_post_windows():
    assert D.LAST_FULL_YEAR == 2025 and list(D.POST_YEARS) == [2023, 2024, 2025] and list(L.POST) == [2023, 2024, 2025]


def test_site_histograms_and_positions_drop_2026():
    df = frame()
    assert (df['year'] == 2026).any()
    h = S.histograms(df, bands=False)
    for s, years in h.items():
        if not years:
            continue
        assert max(int(y) for y in years) == 2025 and '2026' not in years
    assert 'partial' not in json.dumps(h)
    ps = pd.DataFrame([dict(paper_id=f'p{i}', pidx=j, p=0.5) for i in range(len(df)) for j in range(2)])
    cuts = {f'p{i}': 0.1 for i in range(len(df))}
    pos = S.position(df, ps, cuts)
    n_post = int(np.sum(pos['all']['post']['total']))
    assert n_post == 2 * int(df['year'].between(2023, 2025).sum())


def test_yearly_validation_table_drops_2026():
    t = V.yearly_table(frame())
    assert t['year'].max() == 2025 and t['year'].min() == 2016


def test_event_study_and_did_end_at_2025():
    rng = np.random.default_rng(0)
    rows = [dict(lab_id=f'l{lab}', year=y, dose=0.3, y=rng.normal()) for lab in range(60) for y in list(range(2017, 2022)) + list(range(2023, 2027))]
    t = L.did_table(pd.DataFrame(rows), 'y', 'dose', boot=20)
    assert t[t['spec'] == 'event']['year'].max() == 2025


def test_committed_site_json_has_no_2026():
    d = Path(__file__).resolve().parents[1] / 'ai-writing' / 'diversity' / 'site-data'
    for f in sorted(d.glob('ai_hist.json')):
        series = json.loads(f.read_text())['series']
        assert all('2026' not in years for years in series.values())
    import gzip
    for f in sorted(d.glob('labs_ai_hist_*.json*')):
        raw = gzip.open(f, 'rt').read() if f.suffix == '.gz' else f.read_text()
        assert all(r['year'] <= 2025 for r in json.loads(raw)['labs'])
