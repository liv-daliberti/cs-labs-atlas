"""AI-pages data (ai-writing/dose/ai_pages*.py, site-data/v2): owner rule no 2026 anywhere (a partial year; post = 2023-2025), the matched-test and
slope estimators on synthetic data with a planted effect, and the headline sentences re-rendered from their stored values."""
# ruff: noqa: E402
import gzip
import json
import re
from pathlib import Path

import pytest

V2 = Path(__file__).resolve().parents[1] / 'ai-writing' / 'diversity' / 'site-data' / 'v2'
SKIP_KEYS = {'ids', 'titles', 'id', 'name', 'label', 'keywords', 'pi', 'lab', 'lab_id', 'site_lab', 'site', 'field', 'fields', 'description', 'sizes'}


def read(p):
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def walk(o, path=''):
    """(path, key-or-value) pairs of a JSON tree, skipping free-text fields (titles, ids, labels), which may name a conference year."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + '/' + str(k), str(k)
            if k not in SKIP_KEYS:
                yield from walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        if o and all(isinstance(x, (int, float)) for x in o[:50]):
            return
        for i, v in enumerate(o):
            yield from walk(v, path + f'/{i}')
    elif isinstance(o, str):
        yield path, o


def files():
    return sorted(p for p in V2.glob('*.json*')) if V2.exists() else []


def test_v2_files_exist_and_carry_no_2026():
    fs = files()
    names = {p.name for p in fs}
    for want in ('map_index.json', 'map_density.json', 'lab_scatter.json.gz', 'ai_use.json.gz', 'matched_test.json', 'event_study.json', 'fig3_nine_schools.json', 'headline.json'):
        assert want in names, want
    bad = []
    for p in fs:
        for where, tok in walk(read(p)):
            if re.search(r'(?<![\w:.-])2026(?![\w-])', tok):
                bad.append((p.name, where, tok[:60]))
    assert not bad, bad[:5]


def test_year_arrays_stop_at_2025():
    use = read(V2 / 'ai_use.json.gz')
    assert use['meta']['years'] == [2016, 2025]
    assert all(len(t['n']) == 10 for t in use['topics']) and all(len(f['n']) == 10 for f in use['fields'])
    dens = read(V2 / 'map_density.json')
    assert max(int(y) for y in dens['years']) == 2025 and dens['pre']['years'] == '2016-2022' and dens['post']['years'] == '2023-2025'
    idx = read(V2 / 'map_index.json')
    assert idx['meta']['years'] == [2016, 2025]
    for s, n in idx['meta']['shards'].items():
        sh = read(V2 / f'map_{s}.json.gz')
        assert sh['n'] == n == len(sh['x']) == len(sh['ids']) == len(sh['year']) and max(sh['year']) <= 9 and min(sh['year']) >= 0
        assert max(sh['x']) < 4096 and max(sh['y']) < 4096
    ev = read(V2 / 'event_study.json')
    assert ev['meta']['years'] == [2016, 2017, 2018, 2019, 2020, 2023, 2024, 2025]
    for m in ev['models'].values():
        for o in m.values():
            for d in o.values():
                assert all(2016 <= e['year'] <= 2025 for e in d['event'])
    lab = read(V2 / 'lab_scatter.json.gz')
    assert lab['meta']['pre'] == '2016-2022' and lab['meta']['post'] == '2023-2025'
    mt = read(V2 / 'matched_test.json')
    for p in mt['meta']['populations'].values():
        a, b = p['years'].split('-')
        assert 2016 <= int(a) <= int(b) <= 2025
    assert read(V2 / 'headline.json')['meta']['last_year'] == 2025


def test_map_ids_are_reader_keys_and_labs_link():
    idx = read(V2 / 'map_index.json')
    for s in ('princeton', 'mit'):
        sh = read(V2 / f'map_{s}.json.gz')
        assert all(i.startswith('atl:w:') for i in sh['ids'][:200])
        assert len(read(V2 / f'map_titles_{s}.json.gz')['titles']) == sh['n']
        assert max(sh['lab']) < len(idx['labs'])
    released = [l for l in idx['labs'] if l['school'] in ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan')]
    assert sum(l['site'] is not None for l in released) / len(released) > 0.95
    assert all(l['school'] in ('princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan') for l in idx['labs'])
    assert not (V2 / 'map_gatech.json.gz').exists() and not (V2 / 'map_uchicago.json.gz').exists()
    assert all(l['school'] not in ('gatech', 'uchicago') for l in read(V2 / 'lab_scatter.json.gz')['labs'])
    assert read(V2 / 'matched_test.json')['wording']


def test_total_size_budget():
    assert sum(p.stat().st_size for p in files()) < 8 * 1024 * 1024


def test_headline_claims_re_render_from_values():
    pytest.importorskip('pandas')
    import ai_pages_headline as H
    doc = read(V2 / 'headline.json')
    assert 4 <= len(doc['findings']) <= 6
    for f in doc['findings']:
        assert f['claim'] == H.RENDER[f['id']](f['values'])
        assert f['cannot_conclude'] and f['evidence']['page'] and f['evidence']['anchor'] and f['number']['value'] is not None


np = pytest.importorskip('numpy')
pd = pytest.importorskip('pandas')

import ai_pages as A
import ai_pages_more as M


def test_constants_post_2023_2025_and_no_2026():
    assert A.LAST == 2025 and A.POST == [2023, 2024, 2025] and A.PRE[-1] == 2022 and max(A.YEARS) == 2025 and max(A.PLACEBO) == 2021


def planted(n=4000, effect=-0.03, seed=0):
    rng = np.random.default_rng(seed)
    cell = rng.integers(0, 40, n)
    flag = (rng.random(n) < 0.2 + 0.01 * (cell % 10)).astype(float)
    v = 0.5 + 0.1 * (cell % 7) + effect * flag + 0.05 * rng.normal(size=n)   # cells differ a lot: an unmatched difference is confounded
    return v, flag, cell


def test_cell_effect_recovers_planted_effect_and_beats_the_raw_difference():
    v, flag, cell = planted()
    est, wa, cells = M.cell_effect(v, flag, cell, np.ones(len(v)))
    assert abs(est - (-0.03)) < 0.01 and cells == 40 and wa > 0
    raw = M.raw_effect(v, flag, np.ones(len(v)))
    assert abs(raw - (-0.03)) > abs(est - (-0.03))    # the raw gap is confounded by the cell mix, the matched one is not


def test_cell_effect_ignores_cells_with_one_group_and_nan_rows():
    v = np.array([1.0, 2.0, 3.0, np.nan, 5.0]); flag = np.array([1.0, 0.0, 1.0, 0.0, 1.0]); cell = np.array([0, 0, 1, 1, 2])
    est, wa, cells = M.cell_effect(v, flag, cell, np.ones(5))
    assert cells == 1 and abs(est - (1.0 - 2.0)) < 1e-12


def test_placebo_threshold_flags_the_same_share():
    rng = np.random.default_rng(1)
    pre = np.where(rng.random(5000) < 0.7, 0.0, rng.beta(1, 6, 5000))
    post = np.where(rng.random(5000) < 0.5, 0.0, rng.beta(1, 2, 5000))
    t, share = M.placebo_threshold(pre, post)
    assert abs((pre >= t).mean() - share) < 0.02 and t > 0


def test_set_diff_dispersion_and_vendi_directions():
    rng = np.random.default_rng(0)
    d = 16
    wide = rng.normal(size=(60, d)); wide /= np.linalg.norm(wide, axis=1, keepdims=True)
    tight = rng.normal(size=(1, d)) + 0.1 * rng.normal(size=(60, d)); tight /= np.linalg.norm(tight, axis=1, keepdims=True)
    Z = np.vstack([wide, tight])
    dd, dv = M.set_diff(Z, np.arange(60), np.arange(60, 120))
    assert dd > 0 and dv > 0


def test_huber_slope_finds_planted_slope_with_controls():
    rng = np.random.default_rng(2)
    n = 300
    d = pd.DataFrame(dict(dose=rng.random(n), school=rng.choice(['a', 'b', 'c'], n), log_n_pre=rng.normal(size=n), log_n_post=rng.normal(size=n)))
    d['change'] = 0.8 * (d['dose'] - d['dose'].mean()) / d['dose'].std() + 0.3 * rng.normal(size=n)
    b, lo, hi, k = A.huber_slope(d, 'change', 'dose', B=100, seed=0)
    assert k == n and lo < b < hi and abs(b - 0.936) < 0.06 and lo > 0.5


def test_topic_kinds_from_labels():
    assert A.kind_of('transformers, kv, llm, tokens', 'x') == 'llm'
    assert A.kind_of('in-context, incontext learning, llms', '') == 'llm'
    assert A.kind_of('gradient descent, relu, sgd, twolayer', 'learning, neural') == 'ml'
    assert A.kind_of('voltage, electricity, charging, converter', 'grids, dc, renewable') == 'other'


def test_box_stats_whiskers_within_1p5_iqr():
    v = np.r_[np.linspace(0, 1, 99), 50.0]
    b = M.box_stats(v)
    assert b['whishi'] < 2 and b['n_outliers'] == 1 and b['q1'] < b['med'] < b['q3']
