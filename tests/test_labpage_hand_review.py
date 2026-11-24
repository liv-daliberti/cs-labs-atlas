"""Reviewed source limits survive a regenerated proposal and its native import."""
from collections import Counter, defaultdict
import copy
import json
from types import SimpleNamespace

import pytest

import labpage_audit as L
from pihier import students


@pytest.fixture
def audit_files(tmp_path, monkeypatch):
    monkeypatch.setattr(L.P, 'data', lambda fn, school=None, root=None: tmp_path / fn)
    monkeypatch.setattr(L.P, 'data_w', lambda fn, school=None: tmp_path / fn)
    monkeypatch.setattr(L, 'Kit', lambda school: None)
    monkeypatch.setattr(L, 'school_summary', lambda *args: {})
    monkeypatch.setattr(L, 'onboarding', lambda school: True)
    monkeypatch.setattr(L, 'fix_titles_from_arxiv', lambda rows, **kwargs: None)
    monkeypatch.setattr(L, 'withhold_heading_conflict', lambda kit, school, row: row)
    monkeypatch.setattr(L, 'withhold_bio_degree_role', lambda row: row)
    return tmp_path / 'labpage-additions.json'


@pytest.mark.parametrize('decision', ['membership_only', 'alumni_membership_only'])
def test_membership_review_survives_regeneration_and_native_import(audit_files, tmp_path, monkeypatch, decision):
    review = [{'pi': 'Professor Example', 'name': 'Jane Researcher', 'decision': decision}]
    audit_files.write_text(json.dumps({'hand_review_students': review}))
    row = dict(pi='Professor Example', name='Jane Researcher', role='undergraduate', years=None,
               relationship='advising', alumni=False, section='current', url='https://example.edu/group', sha256='a' * 64,
               quote='Current group members: Jane Researcher (undergraduate).')
    original = copy.deepcopy(row)
    for _ in range(2):
        L.write_audit('test', [], [row], [])
        proposal = json.loads(audit_files.read_text())
        assert proposal['hand_review_students'] == review
        expected = dict(row, relationship='membership')
        if decision == 'alumni_membership_only':
            expected.update(alumni=True, section='alumni')
        assert proposal['students'] == [expected]
    assert row == original

    monkeypatch.setattr(students, 'accepted_additions', lambda *args: proposal['students'])
    ctx = SimpleNamespace(here=tmp_path, school='test', pis=[dict(pi='Professor Example')], ge={}, n=Counter())
    native = defaultdict(dict)
    students.researched(ctx, native, {})
    member, = native['Professor Example'].values()
    assert member['roles'] == ['undergraduate']
    relation, = member['relations']
    assert relation['type'] == 'researched_membership'
    assert relation['role'] == 'undergraduate'
    assert relation['years'] == []


@pytest.mark.parametrize('decision', ['rejected', 'held'])
def test_paper_title_review_survives_regeneration(audit_files, decision):
    review = [{'pi': 'Professor Example', 'title': 'Unproven school paper', 'decision': decision}]
    audit_files.write_text(json.dumps({'hand_review_papers': review}))
    papers = [dict(pi='Professor Example', title='Unproven school paper'),
              dict(pi='Professor Example', title='Supported paper')]
    for _ in range(2):
        L.write_audit('test', [], [], papers)
        proposal = json.loads(audit_files.read_text())
        assert proposal['papers'] == [papers[1]]
        assert proposal['hand_review_papers'] == review
