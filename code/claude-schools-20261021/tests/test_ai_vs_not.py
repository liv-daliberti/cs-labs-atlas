"""AI-written vs not (ai-writing/dose/ai_vs_not*.py, site-data/v2/ai_vs_not.json[.gz]): group definitions, blank bands, no 2026, generated sentences."""
# ruff: noqa: E402
import gzip
import json
import re
from pathlib import Path

import pytest

V2 = Path(__file__).resolve().parents[1] / 'ai-writing' / 'diversity' / 'site-data' / 'v2'


def doc():
    for n in ('ai_vs_not.json', 'ai_vs_not.json.gz'):
        p = V2 / n
        if p.exists():
            raw = p.read_bytes()
            return json.loads(gzip.decompress(raw) if n.endswith('.gz') else raw)
    pytest.skip('ai_vs_not.json is generated (ai_vs_not.py assemble)')


def cells(d):
    for m, b in d['models'].items():
        for var, ts in b.items():
            for t, scopes in ts.items():
                for sc, c in scopes.items():
                    yield m, var, t, sc, c


def test_shape_no_2026_and_all_nine_schools():
    d = doc()
    assert d['meta']['years'] == [2016, 2025] and d['meta']['ts'] == [1, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
    assert set(d['meta']['released']) == {'princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech'}
    assert d['meta']['released']['gatech'] is False and d['meta']['released']['princeton'] is True
    assert 'all' in d['meta']['scopes']
    assert not re.search(r'(?<![\w:.-])2026(?![\w-])', json.dumps({k: v for k, v in d.items() if k not in ('models', 'labs')}))
    for m, var, t, sc, c in cells(d):
        assert len(c['n']) == 10
        for met in c['m'].values():
            for ser in met.values():
                assert all(len(ser[k]) == 10 for k in ('gap', 'lo', 'hi'))


def test_blank_below_the_minimum_group_size_and_bands_contain_gap():
    d = doc()
    seen = 0
    for m, var, t, sc, c in cells(d):
        for i, n in enumerate(c['n']):
            for met in c['m'].values():
                for ser in met.values():
                    g = ser['gap'][i]
                    if n is None or min(n) < 20:
                        assert g is None, (m, var, t, sc, i, n)
                    elif g is not None and ser['lo'][i] is not None:
                        seen += 1
                        assert ser['lo'][i] <= ser['hi'][i]
    assert seen > 100


def test_group_sizes_shrink_with_the_cutoff_and_not_group_is_fixed_band():
    d = doc()
    b = d['models'][d['meta']['headline_model']]['cut']
    for sc in ('all', 'cmu'):
        for y in (7, 8, 9):                       # 2023-2025
            na = [b[str(t)][sc]['n'][y][0] for t in d['meta']['ts'] if b[str(t)][sc]['n'][y] is not None]
            assert na == sorted(na, reverse=True)
    # pre-2023 AI-written groups at high cutoffs are tiny: blank
    assert all(b['75']['all']['m']['vendi']['orig']['gap'][i] is None for i in range(0, 6))
    assert d['meta']['placebo_cut']['25'] is not None


def test_sentences_cover_every_metric_and_name_both_versions():
    d = doc()
    s = d['sentences']['text']
    assert set(s) == set(d['meta']['metrics'])
    for k, v in s.items():
        assert v.startswith('At >= 25% flagged') and '2025' in v
        if not d['meta']['metrics'][k]['wording_invariant']:
            assert 'wording held constant' in v


def test_sentence_generator_directions():
    pytest.importorskip('pandas')
    import ai_vs_not_site as S
    c = dict(n=[None] * 9 + [[500, 4000]], m={'vendi': dict(orig=dict(gap=[None] * 9 + [-2.0], lo=[None] * 9 + [-3.0], hi=[None] * 9 + [-1.0]),
                                                           rewritten=dict(gap=[None] * 9 + [-0.1], lo=[None] * 9 + [-1.0], hi=[None] * 9 + [0.8]))})
    t = S.sentence('vendi', c)
    assert 'lower' in t and 'no distinguishable gap' in t and '500' in t
    c['m']['vendi']['orig'] = dict(gap=[None] * 9 + [2.0], lo=[None] * 9 + [1.0], hi=[None] * 9 + [3.0])
    assert 'higher' in S.sentence('vendi', c)
