import copy

import pytest

from home_departments_school import apply_reviewed_homes


def test_sourced_home_correction_preserves_the_computing_appointment():
    rows = [dict(name='Stephen Casper', home_department='Computer Science', also=[], status='accepted')]
    evidence = dict(url='https://school.example/faculty/casper', sha256='a' * 64,
                    quote='Stephen Casper is an Assistant Professor of Public Policy at the Kennedy School.')
    overrides = {'Stephen Casper': dict(home_department='Harvard Kennedy School', home_department_evidence=[evidence],
                                       why_home_department='Official profile states the home school.')}
    result = apply_reviewed_homes(rows, overrides, lambda h: h.replace('Harvard ', ''))
    assert result[0]['home_department'] == 'Kennedy School'
    assert result[0]['also'] == ['Computer Science']
    assert result[0]['evidence'] == evidence
    assert result[0]['reviewed_home_evidence'] == [evidence]


@pytest.mark.parametrize('evidence', [[], [{'url': 'https://school.example', 'quote': 'Professor'}],
                                      [{'url': 'https://school.example', 'sha256': 'not-a-hash', 'quote': 'Professor'}],
                                      [{'url': 'https://school.example', 'sha256': 'a' * 64, 'quote': ''}]])
def test_unsourced_home_decision_is_refused(evidence):
    with pytest.raises(SystemExit, match='requires evidence'):
        apply_reviewed_homes([dict(name='A Person')], {'A Person': dict(home_department='Law', home_department_evidence=evidence)}, lambda h: h)


def test_homes_without_reviewed_decisions_are_unchanged():
    rows = [dict(name='A Person', home_department='Computer Science', also=['Mathematics'], status='accepted')]
    original = copy.deepcopy(rows)
    assert apply_reviewed_homes(rows, {}, lambda h: h) == original
