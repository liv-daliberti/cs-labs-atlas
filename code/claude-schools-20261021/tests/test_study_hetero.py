"""Heterogeneity layer of the 12-school study (ai-writing/study/study_hetero*.py): groups, field map, multiplicity, planted-effect recovery (numpy/pandas)."""
import numpy as np
import pytest

pytest.importorskip('pandas')
import pandas as pd  # noqa: E402
import study_hetero as H  # noqa: E402
import study_hetero_attr as T  # noqa: E402
import study_hetero_fields as F  # noqa: E402
import study_labstats as LS  # noqa: E402


def test_name_match_and_led_classes():
    assert T.same_person('Jane Q. Smith', 'J. Smith') and T.same_person('José García', 'Jose Garcia')
    assert not T.same_person('Jane Smith', 'John Smith') and not T.same_person('Smith', 'Jane Smith')
    pis, stu = {'Ada Lovelace'}, {'Ben Ng'}
    assert T.led_class('first', ['Ada Lovelace', 'Ben Ng'], pis, stu) == 'pi_led'
    assert T.led_class('last', ['B. Ng', 'Ada Lovelace'], pis, stu) == 'student_led'
    assert T.led_class('last', ['Cy Roe', 'Ben Ng', 'Ada Lovelace'], pis, stu) == 'other'
    assert T.led_class(None, ['A. Lovelace', 'Ben Ng'], pis, stu) == 'pi_led'      # missing position: the byline decides
    assert T.led_class('middle', [], pis, stu) == 'other'


def test_career_tiers_are_fixed_cuts_and_use_cumulative_counts():
    assert [T.tier(a, (10, 20)) for a in (3, 9, 10, 20, 21, 30)] == ['early', 'early', 'mid', 'mid', 'senior', 'senior']
    assert T.tier(None, (10, 20)) is None and T.tier(float('nan'), (10, 20)) is None
    years = {'1999': 1, '2003': 2, '2010': 5}
    assert T.career_first_year(years, 1) == 1999 and T.career_first_year(years, 2) == 2003 and T.career_first_year({}, 1) is None
    assert T.appt_start([{'start': '2015'}, {'start': '2009-09'}, {'start': None}]) == 2009 and T.appt_start([]) is None


def test_gras_bands(tmp_path):
    tsv = tmp_path / 'g.tsv'
    rows = ['rank\tname\tcountry'] + [f'{r}\t{n}\tX' for n, r in zip(T.GRAS_NAMES.values(), ['7', '8', '51-75', '1', '4', '3', '51-75', '76-100', '21', '19', '151-200', '201-300'])]
    tsv.write_text('\n'.join(rows))
    b = T.gras_bands(tsv)
    assert b['mit'][2] == 'top10' and b['harvard'][2] == 'r11_50' and b['gatech'][2] == 'r11_50' and b['washu'][2] == 'r51_300' and b['epfl'][1] == 51


def test_field_rules_venue_first_then_topic():
    cs = {F.norm_venue(v) for v in ('Annual Symposium on Foundations of Computer Science', 'ACM SIGCOMM Conference (SIGCOMM)', 'neural information processing systems',
                                    'Lecture notes in computer science', 'IEEE International Conference on Robotics and Automation', 'CHI Conference on Human Factors in Computing Systems')}
    c = lambda v, t=None, s=None, f=None: F.classify([v], cs, t, s, f)       # noqa: E731
    assert c('Annual Symposium on Foundations of Computer Science')[0] == 'theory'
    assert c('ACM SIGCOMM Conference (SIGCOMM)')[::2] == ('systems', 'venue')
    assert c('neural information processing systems')[0] == 'ml_ai'
    assert c('CHI Conference on Human Factors in Computing Systems')[0] == 'other'
    rob = c('IEEE International Conference on Robotics and Automation')
    assert rob[0] == 'other' and rob[1] == 'ml_ai'                         # robotics is 'other' unless the alternative map is used
    assert c('Lecture notes in computer science', 'Distributed systems and fault tolerance', 'Computer Networks and Communications', 'Computer Science')[::2] == ('systems', 'topic')
    assert c('Nature', 'Neural Dynamics in Cortex', None, 'Neuroscience')[0] == 'other'               # the field gate keeps a neuroscience 'neural' topic out of ml_ai
    assert c('Unlisted Journal', None, 'Artificial Intelligence', 'Computer Science')[::2] == ('ml_ai', 'subfield')
    assert c('Unlisted Journal') == ('other', 'other', 'none')
    assert c('Unlisted Journal', 'Complexity and Algorithms in Graphs', None, 'Mathematics')[0] == 'theory'


def test_multiplicity_adjustments():
    p = np.array([0.001, 0.01, 0.02, 0.04, 0.5])
    h, b = H.holm(p), H.bh(p)
    assert np.allclose(h, [0.005, 0.04, 0.06, 0.08, 0.5]) and np.allclose(b, [0.005, 0.025, 0.0333333, 0.05, 0.5])
    assert (h >= p).all() and (b >= p).all() and (h >= b - 1e-12).all()
    assert H.normal_p(0.0, np.random.default_rng(0).normal(size=200)) == pytest.approx(1.0)
    assert H.normal_p(5.0, np.random.default_rng(0).normal(size=200)) < 1e-6


def _frame(rng, nl=60):
    labs = [f'l{i}' for i in range(nl)]
    rows = []
    for i, lab in enumerate(labs):
        grp = 'early' if i % 2 == 0 else 'senior'
        for y in LS.YEARS:
            for j in range(12):
                p = (0.4 if (y >= 2023 and grp == 'early') else 0.05)
                rows.append((f'{lab}-{y}-{j}', 'princeton' if i < nl // 2 else 'cmu', lab, y, grp, float(rng.random() < p)))
    d = pd.DataFrame(rows, columns=['k', 'school', 'lab_id', 'year', 'career', 'heavy_main'])
    d['r'] = np.arange(len(d))
    return d


def test_planted_heterogeneity_is_recovered_and_placebo_is_flat():
    rng = np.random.default_rng(1)
    d = _frame(rng)
    labs = np.sort(d.lab_id.unique())
    sch = d.drop_duplicates('lab_id').set_index('lab_id').school.reindex(labs).to_numpy()
    mats = H.ratio_matrices(d, labs, 'career', ['early', 'senior'], 'heavy_main')
    W = LS.weights(sch, 300, 5)
    ser, eff, pr = H.estimate(mats, W, lambda x: x, dict(outcome='heavy_main'))
    row = pr[pr.contrast == 'post_minus_pre'].iloc[0]
    assert 0.2 < row.est < 0.5 and row.lo > 0.1 and row.p < 1e-4          # early minus senior change is about +0.35
    plc = pr[pr.contrast == 'placebo_2019_21_minus_2016_18'].iloc[0]
    assert plc.lo < 0 < plc.hi
    assert set(eff.group) == {'early', 'senior'} and len(ser) == 2 * len(LS.YEARS)


def test_embedding_statistics_match_brute_force():
    rng = np.random.default_rng(2)
    n = 90
    d = pd.DataFrame({'k': [f'p{i}' for i in range(n)], 'school': 'princeton', 'lab_id': rng.choice(['a', 'b', 'c'], n), 'year': 2020, 'g': rng.choice(['x', 'y'], n)})
    d['r'] = np.arange(n)
    V = rng.normal(size=(n, 6)).astype(np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    labs = np.array(['a', 'b', 'c'])
    em = H.emb_matrices(d, V, labs, 'g', ['x', 'y'], 2)
    t = 2020 - LS.YEARS[0]
    for gi, g in enumerate(('x', 'y')):
        for li, lab in enumerate(labs):
            ix = d.index[(d.lab_id == lab) & (d.g == g)].to_numpy()
            if len(ix) < 2:
                continue
            within = np.mean([1 - V[i] @ V[j] for i in ix for j in ix if i != j])
            S, N = em[g]['within_lab']
            assert 1 - S[li, t] / N[li, t] == pytest.approx(within, abs=1e-5)
            others = d.index[d.lab_id != lab].to_numpy()
            l2s = np.mean([1 - V[i] @ V[j] for i in ix for j in others])
            S, N = em[g]['lab_to_school']
            assert 1 - S[li, t] / N[li, t] == pytest.approx(l2s, abs=1e-5)


def test_frame_restricted_columns_composition_and_quantile_groups():
    rng = np.random.default_rng(3)
    n = 400
    hp = pd.DataFrame({'k': [f'p{i}' for i in range(n)], 'school': 'mit', 'lab_id': [f'l{i % 40}' for i in range(n)], 'pi': 'x', 'year': rng.choice(LS.YEARS, n),
                       'led': rng.choice(['pi_led', 'student_led', 'other'], n), 'field': rng.choice(['theory', 'systems', 'ml_ai', 'other'], n),
                       'gras': 'top10', 'career': 'senior', 'age_any': [float(i % 40) for i in range(n)]})
    pan = pd.DataFrame({'k': hp.k, 'paper_id': hp.k, 'flag_abstract': 1.0, 'ai_share_main': 0.5, 'ai_share_main_appendix': 0.1, 'trained_on_v3': False})
    d = H.frame(pan, hp)
    assert (d.loc[d.field != 'ml_ai', 'led_in_ml'].isna()).all() and (d.loc[d.field == 'ml_ai', 'led_not_ml'].isna()).all()
    assert (d.heavy_main == 1).all() and (d.heavy_main_appendix == 0).all()
    youngest = d[d.career_t3 == 't1_youngest'].age_any.max()
    assert youngest <= d[d.career_t3 == 't3_oldest'].age_any.min()          # tertile 1 holds the smallest career ages
    c = H.composition(d)
    assert np.allclose(c.groupby(['split', 'within', 'group', 'period']).share.sum(), 1.0)
