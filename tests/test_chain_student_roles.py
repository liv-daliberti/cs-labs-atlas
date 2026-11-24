"""A member withheld by the student-link rules must not become a fictitious missed student link."""
import gzip
import json

import chain_audit as A
import pytest


def fixture(tmp_path, monkeypatch, record, paper_year=2026):
    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'pis.json').write_text(json.dumps([dict(pi='Example PI', names=['Example PI'], personIds=['p'], lab={})]))
    (school / 'students.json').write_text(json.dumps({'Example PI': [dict(person='s', name='Dan Member', **record)]}))
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(pi='Example PI', year=paper_year, work='W1', oa='W1')) + '\n')
    with gzip.open(school / 'student_papers.jsonl.gz', 'wt'):
        pass
    monkeypatch.setattr(A.CO, 'onboarding', lambda school: False)
    return A.audit('princeton', hierarchy=tmp_path)['checks']['links']


@pytest.mark.parametrize('role', ['staff', 'research_scientist', 'research_engineer', 'postdoc_alumnus', 'member'])
def test_nonstudent_or_unproven_members_do_not_require_student_links(tmp_path, monkeypatch, role):
    result = fixture(tmp_path, monkeypatch, dict(roles=[role], relations=[dict(role=role, years=[2026], sources=[])]))
    assert result['n_unexplained'] == 0
    assert result['total'] == 1


@pytest.mark.parametrize('record', [
    dict(roles=['phd'], relations=[dict(role='phd', years=[2026])]),
    dict(roles=['member'], relations=[dict(years=[2026], sources=[dict(quote='PhD Students: Dan Member')])]),
    dict(roles=[], relations=[dict(years=[2026])]),
    dict(roles=['phd', 'postdoc'], relations=[dict(role='phd', years=[2026]), dict(role='postdoc', years=[2020])]),
])
def test_real_student_and_legacy_missing_links_stay_unexplained(tmp_path, monkeypatch, record):
    assert fixture(tmp_path, monkeypatch, record)['n_unexplained'] == 1


def test_later_staff_years_do_not_create_a_missing_student_link(tmp_path, monkeypatch):
    record = dict(roles=['phd', 'staff'], relations=[dict(role='phd', years=[2017]), dict(role='staff', years=[2026])])
    assert A.years_of(record) == [2017]
    assert fixture(tmp_path, monkeypatch, record)['n_unexplained'] == 0
