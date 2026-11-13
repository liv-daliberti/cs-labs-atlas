import copy

import pytest

from home_departments_school import NOT_HOME, apply_reviewed_homes, sourced_pi_key


def test_status_only_professor_title_cannot_supply_an_academic_home():
    assert NOT_HOME.search('Professor, Status-Only York University')
    assert not NOT_HOME.search('Professor, Computer Science')


def test_middle_initial_variant_needs_the_same_sourced_faculty_quote():
    base = {'name': 'Brendan Frey', 'pi_basis': {'sha256': 'abc', 'quote': 'Brendan Frey Professor'}}
    variant = {'name': 'Brendan J. Frey', 'pi_basis': dict(base['pi_basis'])}
    assert sourced_pi_key(base) == sourced_pi_key(variant)
    variant['pi_basis']['quote'] = 'Other professor'
    assert sourced_pi_key(base) != sourced_pi_key(variant)
    variant = {'name': 'Michael Grüninger', 'pi_basis': {'sha256': 'def', 'quote': 'Michael Gruninger Professor'}}
    plain = {'name': 'Michael Gruninger', 'pi_basis': dict(variant['pi_basis'])}
    assert sourced_pi_key(variant) == sourced_pi_key(plain)


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


def _ev(q):
    return [dict(url='https://school.example/person/x', sha256='b' * 64, quote=q)]


def test_R_HOME_01_primary_unresolved_keeps_every_named_unit_visible():
    rows = [dict(name='A Person', home_department='profile', also=[], status='accepted')]
    ov = {'A Person': dict(home_department='Applied Mathematics', primary_unresolved=['Applied Mathematics', 'Computer Science'],
                           home_department_evidence=_ev('Professor of Applied Mathematics and of Computer Science'))}
    row = apply_reviewed_homes(rows, ov, lambda h: h)[0]
    assert row['home_basis'] == 'primary_unresolved'
    assert row['primary_unresolved'] == ['Applied Mathematics', 'Computer Science']
    assert 'Computer Science' in row['also'] and 'Applied Mathematics' not in row['also']


def test_R_HOME_01_primary_unresolved_needs_two_units_with_the_home_among_them():
    rows = [dict(name='A Person', home_department='x', also=[], status='accepted')]
    ov = {'A Person': dict(home_department='Law', primary_unresolved=['Economics', 'Statistics'], home_department_evidence=_ev('q'))}
    with pytest.raises(SystemExit, match='primary_unresolved'):
        apply_reviewed_homes(rows, ov, lambda h: h)


def test_R_HOME_01_stated_primary_is_marked_and_secondary_units_kept():
    rows = [dict(name='A Person', home_department='profile', also=[], status='accepted')]
    ov = {'A Person': dict(home_department='Applied Mathematics', primary_stated=True, also_home_departments=['Electrical Engineering'],
                           home_department_evidence=_ev('Primary Teaching Area Applied Mathematics'))}
    row = apply_reviewed_homes(rows, ov, lambda h: h)[0]
    assert row['home_basis'] == 'primary_stated' and row['also'] == ['profile', 'Electrical Engineering']
