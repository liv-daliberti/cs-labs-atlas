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


@pytest.mark.parametrize('held_count,foreign_pi,wrong_doi,admitted,expected', [
    (2, False, False, False, 'reviewed_paper_hold'),
    (1, False, False, False, 'paper_not_lab_paper'),
    (2, True, False, False, 'paper_not_lab_paper'),
    (2, False, True, False, 'paper_not_lab_paper'),
    (2, False, False, True, 'link_missed'),
])
def test_exact_applied_paper_holds_explain_only_all_held_pi_works(tmp_path, monkeypatch, held_count, foreign_pi, wrong_doi, admitted, expected):
    import hashlib
    school = tmp_path / 'princeton'; school.mkdir()
    pi, student = 'Ada Lovelace', 'Jane Doe'
    (school / 'pis.json').write_text(json.dumps([dict(pi=pi, names=[pi], personIds=['pi1'], lab={}, reviewedOpenAlex=['A1'], periods=[dict(start='2018', end=None, asof='2026')], listings=[])]))
    (school / 'students.json').write_text(json.dumps({pi: [dict(person='s1', name=student, roles=['phd'], relations=[dict(type='researched_advising', years=[2020])])]}))
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(pi=pi, year=2020, work='W1' if admitted else 'W0', oa='W1' if admitted else 'W0')) + '\n')
    with gzip.open(school / 'student_papers.jsonl.gz', 'wt'):
        pass
    decisions = [dict(id=f'hold-{i}', pi='Other PI' if foreign_pi else pi, decision='hold', match=dict(oa=f'W{i}', doi='10.1000/wrong' if wrong_doi else f'10.1000/{i}'), why='Unresolved source representation', reviewed_by='Reviewer', reviewed_at='2026-11-17', evidence=[dict(url='https://example.org/paper', sha256='a'*64, quote='Original byline')]) for i in range(1, held_count+1)]
    review = school / 'paper-claim-review.json'; review.write_text(json.dumps(dict(version=1, school='princeton', decisions=decisions)))
    (school / 'report.json').write_text(json.dumps(dict(paperClaimReview=dict(sha256=hashlib.sha256(review.read_bytes()).hexdigest(), decisions=[dict(d, outcome='held_before_identity') for d in decisions]))))
    inst = 'https://openalex.org/' + D.INST['princeton']
    works = [dict(id=f'W{i}', doi=f'https://doi.org/10.1000/{i}', title=f'Paper {i}', publication_year=2020, publication_date='2020-06-01', type='article', authorships=[dict(author=dict(id=aid), raw_author_name=name, institutions=[dict(id=inst)]) for aid,name in [('A1',pi),('A2',student)]]) for i in (1,2)]
    monkeypatch.setattr(D, 'H', tmp_path); monkeypatch.setattr(D, 'sweep_works', lambda school: iter(works)); monkeypatch.setattr(A.CO, 'onboarding', lambda school: False)
    unchanged = {p:p.read_bytes() for p in school.iterdir()}
    D.run('princeton')
    diagnosis = json.loads((school/'link-diagnosis.json').read_text())['students'][pi+' | s1']
    assert diagnosis['category'] == expected
    assert A.audit('princeton', hierarchy=tmp_path)['checks']['links']['n_unexplained'] == (0 if expected=='reviewed_paper_hold' else 1)
    if expected=='reviewed_paper_hold':
        assert {x for w in diagnosis['works'] for x in w['paper_hold_decisions']} == {'hold-1','hold-2'}
    assert all(p.read_bytes()==raw for p,raw in unchanged.items())
    review.write_text(review.read_text()+' ')
    with pytest.raises(ValueError, match='differs from the native build'):
        D.run('princeton')
