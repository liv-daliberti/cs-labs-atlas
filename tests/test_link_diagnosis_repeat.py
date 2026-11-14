import gzip
import json

import chain_audit as A
import link_diagnosis as D
import pytest


def test_reviewed_exclusions_explain_only_fully_held_lab_matches():
    mine = [{'work': 'https://openalex.org/W1'}, {'work': 'https://openalex.org/W2'}]
    held = {('PI', 'Student', 'https://openalex.org/W1')}
    assert not D.all_lab_matches_reviewed_out(mine, held, 'PI', 'Student')
    held.add(('PI', 'Student', 'https://openalex.org/W2'))
    assert D.all_lab_matches_reviewed_out(mine, held, 'PI', 'Student')
    assert not D.all_lab_matches_reviewed_out(mine, held, 'Other PI', 'Student')
    assert not D.all_lab_matches_reviewed_out([], held, 'PI', 'Student')


def test_diagnosis_survives_repeated_audit_and_failed_refresh(tmp_path, monkeypatch):
    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'pis.json').write_text(json.dumps([dict(pi='Ada Lovelace', names=['Ada Lovelace'],
        personIds=['pi1'], lab={}, reviewedOpenAlex=['A1'], periods=[], listings=[])]))
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [dict(person='s1', name='Jane Doe',
        roles=['phd'], relations=[dict(type='researched_advising', years=[2020])])]}))
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(pi='Ada Lovelace', year=2020, work='W1', oa='W1')) + '\n')
    with gzip.open(school / 'student_papers.jsonl.gz', 'wt'):
        pass
    monkeypatch.setattr(D, 'H', tmp_path)
    monkeypatch.setattr(D, 'sweep_works', lambda school: iter([]))
    monkeypatch.setattr(A.CO, 'onboarding', lambda school: False)
    output = school / 'link-diagnosis.json'

    D.run('princeton')
    first = output.read_bytes()
    assert json.loads(first)['students']['Ada Lovelace | s1']['category'] == 'no_school_work'
    audit = A.audit('princeton', hierarchy=tmp_path)
    assert audit['checks']['links']['n_unexplained'] == 0
    (tmp_path / 'chain-audit.json').write_text(json.dumps({'schools': [audit]}))
    D.run('princeton')
    assert output.read_bytes() == first

    def failed_sweep(school):
        raise RuntimeError('Sweep temporarily unreadable')

    monkeypatch.setattr(D, 'sweep_works', failed_sweep)
    with pytest.raises(RuntimeError, match='temporarily unreadable'):
        D.run('princeton')
    assert output.read_bytes() == first
