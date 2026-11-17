import gzip
import json

import chain_audit as A


def student(quote, **source_extra):
    return dict(person='s1', name='Jane Doe', roles=['phd'], relations=[dict(type='researched_advising', role='phd', years=[2026],
                sources=[dict(url='https://lab.example/people', sha256='a' * 64, quote=quote, **source_extra)])])


def test_capture_year_and_legacy_missing_date_basis_never_prove_a_recent_start():
    assert A.stated_student_start(student('Current Students Jane Doe (Ph.D., G5)', years_basis='capture_date')) is None
    assert A.stated_student_start(student('Current Students Jane Doe PhD Student')) is None
    assert A.stated_student_start(student('Jane Doe PhD 2026')) is None  # graduation is not arrival
    assert A.stated_student_start(student('Jane Doe Incoming PhD Student, 2026-present')) is None


def test_explicit_dated_start_is_positive_evidence_and_older_start_stays_older():
    assert A.stated_student_start(student('Jane Doe PhD student since 2025')) == 2025
    assert A.stated_student_start(student('Jane Doe (PhD, 2023-)')) == 2023
    assert A.stated_student_start(student('Jane Doe joined the lab in 2026')) == 2026
    assert A.stated_student_start(student('Jane Doe PhD Student. John Smith PhD student since 2025')) is None


def test_program_code_between_role_and_dated_range_is_not_a_graduation_year():
    assert A.stated_student_start(student('Jane Doe PhD CSE 2025–present')) == 2025
    assert A.stated_student_start(student('Jane Doe PhD IIP 2026–present')) == 2026
    assert A.stated_student_start(student('Jane Doe PhD CSE 2026')) is None


def test_chain_audit_keeps_unlinked_established_current_student_open(tmp_path, monkeypatch):
    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'pis.json').write_text(json.dumps([dict(pi='Ada Lovelace', names=['Ada Lovelace'], personIds=['pi1'], lab={})]))
    (school / 'report.json').write_text('{}')
    (tmp_path / 'census-overrides.json').write_text('{}')
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(pi='Ada Lovelace', year=2026, work='W1', oa='W1')) + '\n')
    monkeypatch.setattr(A, 'H', tmp_path)

    def links(quote):
        (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [student(quote)]}))
        return A.audit('princeton')['checks']['links']

    assert links('Current Students Jane Doe (Ph.D., G5)')['n_unexplained'] == 1
    recent = links('Jane Doe PhD student since 2025')
    assert recent['n_unexplained'] == 0
    assert sum(recent['explained'].values()) == 1
    postdoc = student('Jane Doe postdoctoral fellow 2024-2026')
    postdoc['roles'] = ['postdoc']
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [postdoc]}))
    audited = A.audit('princeton')['checks']['links']
    assert audited['n_unexplained'] == 0
    assert audited['explained']['postdoc is a lab member, not a student-paper advisee'] == 1

    # The link builder excludes the same postdoc-only record even when source
    # imports retain synonymous or additional nonstudent membership labels.
    postdoc['roles'] = ['postdoc', 'postdoctoral_researcher', 'member', 'Research Scientist']
    postdoc['relations'][0]['role'] = 'postdoctoral_researcher'
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [postdoc]}))
    audited = A.audit('princeton')['checks']['links']
    assert audited['n_unexplained'] == 0
    assert audited['explained']['postdoc is a lab member, not a student-paper advisee'] == 1

    # An independently recorded student role still requires a student link or
    # evidence explaining its absence, including student cues on member rows.
    postdoc['roles'].append('phd')
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [postdoc]}))
    assert A.audit('princeton')['checks']['links']['n_unexplained'] == 1
    postdoc['roles'] = ['postdoc', 'member']
    postdoc['relations'][0]['sources'][0]['quote'] = 'PhD Students Jane Doe PhD Student'
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [postdoc]}))
    assert A.audit('princeton')['checks']['links']['n_unexplained'] == 1
