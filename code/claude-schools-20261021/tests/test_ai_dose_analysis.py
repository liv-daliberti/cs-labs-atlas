"""Paper-level dose designs (dose_analysis.designs_for) on a synthetic frame with a planted dose effect inside labs."""
# ruff: noqa: E402
import pytest

pytest.importorskip('pandas')
pytest.importorskip('torch', reason='dose_analysis imports the validation module chain')

import numpy as np
import pandas as pd

import dose_analysis as A


def frame(effect, seed=0, n_lab=60, per=25):
    rng = np.random.default_rng(seed)
    lab = np.repeat([f'atl:l:x:{i}' for i in range(n_lab)], per)
    n = len(lab)
    year = rng.integers(2023, 2027, n)
    lab_eff = rng.normal(0, 1, n_lab).repeat(per)
    x = np.clip(rng.beta(1, 4, n) + 0.2 * lab_eff, 0, 1)
    d = pd.DataFrame(dict(y=effect * x + lab_eff + rng.normal(0, .2, n), ai_share=x, flag_abstract=(x > .25).astype(float), lab0=lab, scope_id=lab, year=year, school='mit',
                          topic=rng.choice(list('abcde'), n), llm_topic=rng.random(n) < .1, team_log=rng.normal(size=n), venue_type='journal', oa_status='gold',
                          first_author=[f'a{i // 5}' for i in range(n)]))
    d['topic_year'] = d['topic'] + d['year'].astype(str)
    for b, (lo, hi) in zip(A.BIN_LABELS, ((.05, .25), (.25, .5), (.5, 1.01))):
        d[f'bin_{b}'] = ((d['ai_share'] >= lo) & (d['ai_share'] < hi)).astype(float)
    return d


def test_designs_recover_within_lab_effect():
    d = frame(-0.5)
    rows = A.designs_for(d, 'y', 'ai_share', 'lab', dict(model='m'))
    r = {x['design']: x for x in rows}
    assert {'raw', 'pooled', 'topicyear', 'nollm', 'withinlab', 'author', 'bin 25-50%'} <= set(r)
    assert r['withinlab']['lo'] < -0.5 < r['withinlab']['hi']
    assert r['raw']['beta'] > r['withinlab']['beta']        # lab confounding pushes the pooled slope up
