import json
import pytest

import home_department_registry as H


def row(name='Ann', home='Statistics', **kw):
    return dict(school='uchicago', name=name, home_department=home, status='accepted',
                evidence=dict(url='https://stat.uchicago.edu/faculty', sha256='a' * 64, quote='Ann, Professor'), **kw)


def test_school_local_register_fills_shared_absence_without_other_school_leakage():
    assert H.merge_rows([dict(row(), school='other')], [row()], 'uchicago') == [row()]


def test_local_hold_supersedes_old_shared_acceptance():
    hold = dict(row(), home_department=None, status='hold')
    assert H.merge_rows([row()], [hold], 'uchicago') == [hold]


def test_explicit_local_review_wins_but_inference_cannot_erase_shared_review():
    assert H.merge_rows([row()], [row(home='Computer Science')], 'uchicago') == [row()]
    explicit = row(home='Computer Science', home_basis='primary_stated')
    assert H.merge_rows([row()], [explicit], 'uchicago') == [explicit]


def test_ambiguity_survives_merge_and_does_not_claim_primary():
    r = row(home_basis='primary_unresolved', primary_unresolved=['Statistics', 'Computer Science'])
    assert not H.review(H.merge_rows([], [r], 'uchicago')[0])['primary_resolved']
    assert H.review(r)['primary_unresolved'] == r['primary_unresolved']


def test_release_reader_never_falls_back_to_live_school_register(tmp_path):
    (tmp_path / 'home-departments.json').write_text(json.dumps([row()]))
    assert H.accepted('uchicago', tmp_path) == {'Ann': row()}
    (tmp_path / 'uchicago').mkdir()
    (tmp_path / 'uchicago/home-departments.json').write_text(json.dumps([dict(row(), status='hold')]))
    assert H.accepted('uchicago', tmp_path) == {}


def test_incomplete_evidence_is_not_a_resolved_home():
    assert not H.valid_evidence(dict(row(), evidence=dict(url='u', sha256='not-a-hash', quote='q')))
    assert not H.review(dict(row(), status='hold'))['primary_resolved']


def test_duplicate_sources_may_agree_but_conflicting_decisions_fail():
    same_home = dict(row(), evidence=dict(row()['evidence'], quote='Ann, Associate Professor'))
    assert H.merge_rows([], [row(), same_home], 'uchicago') == [row()]
    with pytest.raises(ValueError, match='conflicting duplicate'):
        H.merge_rows([], [row(), row(home='Computer Science')], 'uchicago')


def test_organized_lab_includes_local_home_and_ambiguity(tmp_path, monkeypatch):
    import gzip
    import organize_tree as T

    school = tmp_path / 'hierarchy/uchicago'
    school.mkdir(parents=True)
    (school / 'pis.json').write_text(json.dumps([dict(pi='Ann', departments=['CS'], lab=dict(name='Ann lab'))]))
    (school / 'students.json').write_text('{}')
    (school / 'copies.json').write_text('{"papers": {}}')
    for name in ('lab_papers', 'student_papers'):
        (school / (name + '.jsonl.gz')).write_bytes(gzip.compress(b''))
    r = row(home_basis='primary_unresolved', primary_unresolved=['Statistics', 'Computer Science'])
    (school / 'home-departments.json').write_text(json.dumps([r]))
    monkeypatch.setattr(T, 'H', tmp_path / 'hierarchy')
    monkeypatch.setattr(T, 'OUT', tmp_path / 'schools')
    monkeypatch.setattr(T, 'stored_files', lambda school: {})
    T.build('uchicago', {})
    lab = json.loads((tmp_path / 'schools/uchicago/labs/ann/lab.json').read_text())
    assert lab['home_department'] == 'Statistics'
    assert lab['home_department_review']['primary_unresolved'] == ['Statistics', 'Computer Science']
    assert not lab['home_department_review']['primary_resolved']


def test_local_home_register_is_part_of_release_package():
    import make_release
    assert 'home-departments-school.json' in make_release.SCHOOL_EXTRA
