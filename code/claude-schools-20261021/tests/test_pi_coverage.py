"""Per-PI coverage ledger (owner 2026-11-12): states, thresholds, honesty rules, gate ratchet."""
import gzip
import json

import pytest

import atlas_paths as P
import pi_coverage as C
import stage_gate as G


def stu(name, role='phd', years=(), src='https://lab.example/people'):
    return dict(person=name, name=name, roles=[role],
                relations=[dict(type='direct_lab_membership', years=list(years), role=role, sources=[dict(url=src)])])


def lp(pi, year, i):
    return dict(pi=pi, year=year, oa=f'W{pi}{year}{i}')


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    (tmp_path / 'u').mkdir()
    C._CACHE.clear()

    def put(name, obj):
        (tmp_path / 'u' / name).write_text(json.dumps(obj))

    def put_gz(name, rows):
        with gzip.open(tmp_path / 'u' / name, 'wt') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
    return put, put_gz


def pi(name, years=(2020, 2026), **kw):
    return dict(pi=name, names=[name], dblp=kw.pop('dblp', ['d']), orcid=[], reviewedOpenAlex=[], departments=['CS'],
                listings=[dict(year=y) for y in years], periods=[], **kw)


def test_appointment_years_prefers_periods_then_listings():
    assert C.appointment_years(pi('A', (2018, 2020)), (2016, 2026)) == [2018, 2019, 2020]
    p = pi('A', (2018, 2020))
    p['periods'] = [dict(start='2023-01-01', end=None)]
    assert C.appointment_years(p, (2016, 2026)) == [2023, 2024, 2025, 2026]
    assert C.appointment_years(dict(pi='B', listings=[]), (2016, 2026)) == []


def test_states_present_reason_gap(tree):
    put, put_gz = tree
    put('pis.json', [pi('Full'), pi('Thin'), pi('Reasoned', dblp=[]), pi('Empty', dblp=[])])
    put('students.json', {'Full': [stu(f'S{i} X', years=[2025]) for i in range(3)], 'Thin': [stu('Only One', years=[2025])]})
    put_gz('lab_papers.jsonl.gz', [lp('Full', 2022, i) for i in range(4)] + [lp('Thin', 2022, 0)])
    put_gz('student_papers.jsonl.gz', [dict(pi='Full', student=f'p{i}', oa=f'W{i}') for i in range(2)])
    put('lab-coverage-reasons.json', {'Reasoned': {
        'students': {'code': 'sources_exhausted', 'why': 'emeritus, no group', 'sources_checked': ['cv', 'page']},
        'papers': {'code': 'sources_exhausted', 'why': 'no papers since 2012', 'sources_checked': ['dblp', 'orcid']}}})
    rows = {r['pi']: r for r in C.ledger('u')}
    assert (rows['Full']['lab_state'], rows['Full']['students_state'], rows['Full']['links_state']) == ('present',) * 3
    assert rows['Thin']['lab_state'] == 'gap' and rows['Thin']['lab_cause'] == 'thin_lab_papers'
    assert rows['Thin']['students_cause'] == 'thin_students' and rows['Thin']['links_state'] == 'gap'
    assert rows['Reasoned']['lab_state'] == rows['Reasoned']['students_state'] == 'reason'
    assert rows['Reasoned']['links_cause'] == 'inherits_students_reason'
    assert rows['Empty']['lab_state'] == 'gap' and rows['Empty']['students_cause'] in ('no_website', 'no_student_evidence')


def test_one_source_or_boilerplate_reason_is_a_gap(tree):
    put, _ = tree
    put('pis.json', [pi('A'), pi('B')])
    put('lab-coverage-reasons.json', {
        'A': {'students': {'code': 'x', 'why': 'researched but one source', 'sources_checked': ['cv']}},
        'B': {'students': {'code': 'x', 'why': C.R.BOILERPLATE + '.', 'sources_checked': ['a', 'b']}}})
    rows = {r['pi']: r for r in C.ledger('u')}
    assert rows['A']['students_state'] == rows['B']['students_state'] == 'gap'
    assert rows['B']['students_cause'].startswith('boilerplate_reason_')


def test_shared_no_identity_hold_is_not_a_reason_but_an_individual_sourced_one_is(tree):
    put, _ = tree
    names = [f'P{i}' for i in range(4)]
    put('pis.json', [pi(n, dblp=[]) for n in names])
    shared = 'PI role reviewed; identity held. https://a.example/x https://b.example/y'
    ov = {n: dict(no_identity=True, why_no_identity=shared) for n in names[:3]}
    ov['P3'] = dict(no_identity=True, why_no_identity='Checked https://a.example/p3 and https://b.example/p3: no papers before the 2025 move.')
    put('census-overrides-school.json', ov)
    rows = {r['pi']: r for r in C.ledger('u')}
    assert all(rows[n]['lab_state'] == 'gap' and rows[n]['lab_cause'] == 'no_identity_anchor_boilerplate_hold' for n in names[:3])
    assert rows['P3']['lab_state'] == 'reason'


def test_undated_thesis_or_profile_rows_do_not_count_but_dated_ones_do():
    undated = [stu(f'T{i} X', role='phd', src='https://dspace.mit.edu/handle/1') for i in range(3)]
    f = C.student_facts(undated)
    assert f['qualifying'] == 0 and f['excluded_undated_weak'] == 3
    dated = [stu(f'T{i} X', role='phd', years=[2019], src='https://dspace.mit.edu/handle/1') for i in range(3)]
    f = C.student_facts(dated)
    assert f['qualifying'] == 3 and f['alumni'] == 3 and f['current'] == 0
    assert C.student_facts([stu('A B', years=[2025])])['current_phd'] == 1


def test_inactive_pi_needs_one_student_active_needs_three(tree):
    put, _ = tree
    put('pis.json', [pi('Gone', (2016, 2020)), pi('Here', (2016, 2026))])
    put('students.json', {'Gone': [stu('Old Alum', role='alumni', years=[2019])], 'Here': [stu('Old Alum', role='alumni', years=[2019])]})
    rows = {r['pi']: r for r in C.ledger('u')}
    assert rows['Gone']['students_state'] == 'present' and rows['Here']['students_state'] == 'gap'


def test_gate_items_follow_the_ratchet(tree, monkeypatch):
    put, _ = tree
    put('pis.json', [pi('A'), pi('B')])
    assert C.gate_items('u', 'papers', 0) == [] and C.gate_items('u', 'students', 0) == []
    assert any('lab_papers' in x for x in C.gate_items('u', 'papers', 3))
    assert {x.split(':')[0] for x in C.gate_items('u', 'students', 3)} == {'PI coverage students', 'PI coverage links'}
    assert C.gate_items('nobuild', 'papers', 3) == []


def test_ratchet_levels_tighten_monotonically_and_level_zero_is_report_only():
    L = C.RATCHET_LEVELS
    assert all(v == 1.0 for v in L[0].values())
    for dim in L[0]:
        assert all(L[i][dim] >= L[i + 1][dim] for i in range(len(L) - 1))
    assert 0 <= C.RATCHET_LEVEL < len(L)


def test_stage_gate_carries_the_counts(tree):
    put, _ = tree
    put('pis.json', [pi('A')])
    put('census-faculty.json', {'faculty': [dict(name='A', is_pi=True, dblp=['d'])]})
    bad, n = G.g5('u')
    assert n['pi_cov_lab_papers_gap'] == 1
