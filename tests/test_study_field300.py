"""Field-300 study (ai-writing/study/field300_*.py): roster, corpus row rules, estimators on fixtures (numpy/pandas; skip without them)."""
import numpy as np
import pytest

pytest.importorskip('pandas')
import pandas as pd  # noqa: E402

import field300_common as F  # noqa: E402
import field300_corpus as K  # noqa: E402
import field300_prep as P  # noqa: E402
import field300_stats as S  # noqa: E402


def test_roster_has_300_cohort_institutions():
    r = F.load_roster()
    assert len(r) == 300 and [x['idx'] for x in r] == list(range(300))
    tiers = pd.Series([x['tier'] for x in r]).value_counts().to_dict()
    assert tiers == {'top10': 10, '11-50': 40, '51-100': 50, '101-200': 100, '201-300': 100}
    assert all(x['cc'] for x in r) and sum(x['english'] for x in r) == 136
    assert len(K.id_table(r)) == 302          # 300 main ids + 2 related ids of the GRAS map (3 rows list one each, one id is shared or absent)


def test_short_int_and_abstract():
    assert F.short_int('https://openalex.org/fields/17') == 17 and F.short_int('W123') == 123 and F.short_int(None) is None
    assert F.abstract_of({'a': [0, 2], 'b': [1]}) == 'a b a' and F.abstract_of(None) == ''


def work(**kw):
    w = dict(id='https://openalex.org/W9', publication_year=2024, type='conference-paper', title='t', language='en',
             authorships=[{'institutions': [{'id': 'https://openalex.org/I1', 'lineage': ['https://openalex.org/I1'], 'country_code': 'US'}]},
                          {'institutions': [{'id': 'https://openalex.org/I1', 'lineage': ['https://openalex.org/I1']},
                                            {'id': 'https://openalex.org/I2', 'lineage': ['https://openalex.org/I2']}]}],
             primary_topic={'id': 'https://openalex.org/T5', 'field': {'id': 'https://openalex.org/fields/17'}, 'subfield': {'id': 'https://openalex.org/subfields/1702'}},
             topics=[], primary_location={'source': {'id': 'https://openalex.org/S7', 'type': 'conference'}}, abstract_inverted_index={'x': [0]},
             referenced_works=['https://openalex.org/W1', 'https://openalex.org/W2'])
    w.update(kw)
    return w


def test_row_rules():
    idt = {'I1': 0, 'I2': 1}
    r, why = K.row_of(work(), idt, set())
    assert why == 'ok' and r['inst'] == [0, 1] and r['inst_n'] == [2, 1] and r['refs'] == [1, 2] and r['abstract'] == 'x' and r['subfield'] == 1702
    assert K.row_of(work(publication_year=2026), idt, set())[1] == 'year'
    assert K.row_of(work(type='dataset'), idt, set())[1] == 'type'
    assert K.row_of(work(authorships=[]), idt, set())[1] == 'inst'
    nc = dict(primary_topic={'id': 'T1', 'field': {'id': 'https://openalex.org/fields/27'}}, topics=[{'field': {'id': 'https://openalex.org/fields/17'}}])
    assert K.row_of(work(**nc), idt, set())[1] == 'cs_any'
    assert K.row_of(work(**nc), idt, {7})[0]['cs_venue'] is True       # a reviewed CS venue admits a non-CS primary topic


def test_english_rule():
    assert P.english('en', 'x') and not P.english('de', 'Zusammenfassung') and P.english(None, 'plain ascii text') and not P.english(None, '这是中文摘要')


def test_cross_distance_excludes_shared_papers():
    rng = np.random.default_rng(0)
    d = 8
    X = rng.normal(size=(7, d))
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    # papers 0-2 belong to institution 0, papers 2-5 to institution 1 (paper 2 to both), paper 6 to neither
    mem = {0: [0, 1, 2], 1: [2, 3, 4, 5]}
    Sm = np.stack([X[mem[i]].sum(0) for i in (0, 1)])
    n = np.array([3., 4.])
    C = np.array([[3., 1.], [1., 4.]])
    D = S.cross_distance(Sm, n, C)
    brute = np.mean([1 - X[a] @ X[b] for a in mem[0] for b in mem[1] if a != b])
    assert abs(D[0, 1] - brute) < 1e-9 and abs(D[0, 1] - D[1, 0]) < 1e-12


def test_mpd_cells_matches_pairwise():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(6, 5))
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    cell = np.zeros((1, 1, 5))
    cell[0, 0] = X.sum(0)
    m = S.mpd_cells(cell, np.array([[6.]]), 5)[0, 0]
    brute = np.mean([1 - X[i] @ X[j] for i in range(6) for j in range(6) if i != j])
    assert abs(m - brute) < 1e-9 and np.isnan(S.mpd_cells(cell, np.array([[6.]]), 7)[0, 0])


def test_jsd_and_entropy():
    P_ = np.array([[1, 0], [0, 1], [.5, .5]])
    J = S.jsd_matrix(P_)
    assert abs(J[0, 1] - 1) < 1e-9 and abs(J[0, 0]) < 1e-9 and abs(J[0, 2] - 0.3112781244591328) < 1e-9
    assert abs(S.entropy_bits([.5, .5]) - 1) < 1e-12 and S.entropy_bits([1, 0]) == 0


def test_pair_draws_point_estimate_and_groups():
    L_ = 6
    X = np.arange(L_ * L_, dtype=float).reshape(L_, L_)
    M = np.ones((L_, L_), bool)
    W = np.ones((3, L_))
    est = S.pair_draws(W, X, M)[0]
    off = X[~np.eye(L_, dtype=bool)].mean()
    assert abs(est - off) < 1e-9
    a = np.array([1, 1, 1, 0, 0, 0], bool)
    sub = X[:3, :3][~np.eye(3, dtype=bool)].mean()
    assert abs(S.pair_draws(W, X, M, a, a)[0] - sub) < 1e-9


def test_multiplicity_adjustments():
    p = np.array([0.001, 0.01, 0.04, 0.5])
    h = S.holm(p)
    assert np.allclose(h, [0.004, 0.03, 0.08, 0.5])
    q = S.bh(p)
    assert np.all(q >= p - 1e-12) and q[0] <= q[1] <= q[2] <= q[3]
    assert np.isclose(q[0], 0.004)


def test_boot_p_detects_a_shifted_distribution():
    rng = np.random.default_rng(2)
    d = rng.normal(1.0, 0.1, 400)
    assert S.boot_p(d, 1.0) < 1e-6 and S.boot_p(rng.normal(0, 0.1, 400), 0.0) > 0.99


def test_group_dimensions_and_family():
    import field300_hetero as H
    inst = pd.DataFrame(F.load_roster())
    inst['size_q'] = np.resize(['Q1 small', 'Q2', 'Q3', 'Q4 large'], 300)
    dims, cons = H.dimensions(inst)
    assert set(dims) == {'tier', 'region', 'country', 'english', 'size'}
    assert dims['english']['English-speaking country'].sum() == 136
    assert len(cons) == 5 + len(dims['region']) + len(dims['country']) + 1 + 4 + 1
