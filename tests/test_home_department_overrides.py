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


def test_charter_ladder_title_supplies_its_listing_department(monkeypatch, tmp_path):
    import json
    import atlas_paths as P
    import census_overrides as CO
    import home_departments_school as H

    cfg = {'departments': [{'code': 'CST', 'name': 'Computer Science and Technology',
                            'title_match': 'computer science'}], 'affiliated_units': [],
           'census': {'rank_words': {'ladder': r'\b(?:reader|university (?:senior )?lecturer)\b'}}}
    # A reader's own dated department listing is the source for the home.
    row = {'name': 'Example Reader', 'titles': ['University Reader'], 'dept': 'CST',
           'observed': '20260101', 'capture_url': 'https://school.example/cst',
           'sha256': 'a' * 64, 'quote': 'Example Reader University Reader'}
    person = {'name': row['name'], 'is_pi': True, 'aliases': [], 'pi_basis': {}}
    for name, value in {'census-faculty.json': {'faculty': [person]}, 'rows.json': [row]}.items():
        (tmp_path / name).write_text(json.dumps(value))
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(P, 'data', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(P, 'data_w', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(CO, 'section', lambda key: {})
    H.main('cambridge')
    result = json.loads((tmp_path / 'home-departments-school.json').read_text())
    assert result[0]['status'] == 'accepted'
    assert result[0]['home_department'] == 'Computer Science and Technology'
    assert result[0]['evidence']['quote'] == row['quote']


def test_sourced_correction_does_not_turn_a_disproved_home_into_an_appointment():
    original_evidence = _ev('A profile collected under a CS directory')[0]
    rows = [dict(name='A Person', home_department='Computer Science', also=['Mathematics'],
                 status='accepted', evidence=original_evidence)]
    decision = dict(home_department='Artificial Intelligence', primary_stated=True,
                    home_department_evidence=_ev('School/Department: Artificial Intelligence'),
                    also_home_departments=['Electrical Engineering'],
                    superseded_home_department='Computer Science',
                    why_superseded_home_department='CS was inferred from the directory host, not a stated appointment.')
    result = apply_reviewed_homes(rows, {'A Person': decision}, lambda h: h)
    assert result[0]['home_department'] == 'Artificial Intelligence'
    assert result[0]['also'] == ['Mathematics', 'Electrical Engineering']
    assert result[0]['superseded_home_department'] == dict(
        home_department='Computer Science', evidence=original_evidence,
        reason=decision['why_superseded_home_department'])
    once = copy.deepcopy(result)
    assert apply_reviewed_homes(result, {'A Person': decision}, lambda h: h) == once


@pytest.mark.parametrize('change, message', [
    ({'why_superseded_home_department': ''}, 'researched reason'),
    ({'superseded_home_department': True}, 'requires a unit'),
    ({'superseded_home_department': 'Law'}, 'does not match'),
    ({'home_department': 'Computer Science'}, 'conflicts'),
    ({'also_home_departments': ['Computer Science']}, 'conflicts'),
    ({'primary_unresolved': ['Artificial Intelligence', 'Computer Science']}, 'conflicts'),
    ({'primary_unresolved': ['Artificial Intelligence', 'Mathematics']}, 'conflicts'),
])
def test_home_correction_rejects_stale_or_conflicting_supersession(change, message):
    rows = [dict(name='A Person', home_department='Computer Science', also=['Mathematics'])]
    original = copy.deepcopy(rows)
    decision = dict(home_department='Artificial Intelligence',
                    home_department_evidence=_ev('School/Department: Artificial Intelligence'),
                    superseded_home_department='Computer Science',
                    why_superseded_home_department='Incorrect directory inference.')
    decision.update(change)
    with pytest.raises(SystemExit, match=message):
        apply_reviewed_homes(rows, {'A Person': decision}, lambda h: h)
    assert rows == original


def test_superseded_home_reapplication_compares_canonical_units_and_preserves_raw_history():
    normalize = lambda unit: {'国家网络安全学院': 'Cyber Science and Engineering'}.get(unit, unit)
    rows = [dict(name='A Person', home_department='国家网络安全学院', also=[])]
    decision = dict(home_department='Artificial Intelligence', primary_stated=True,
                    home_department_evidence=_ev('School/Department: Artificial Intelligence'),
                    superseded_home_department='Cyber Science and Engineering',
                    why_superseded_home_department='Previous unit was inferred incorrectly.')
    once = copy.deepcopy(apply_reviewed_homes(rows, {'A Person': decision}, normalize))
    assert once[0]['superseded_home_department']['home_department'] == '国家网络安全学院'
    assert apply_reviewed_homes(rows, {'A Person': decision}, normalize) == once


def test_supersession_cannot_leave_an_existing_unresolved_primary_claim_contradictory():
    rows = [dict(name='A Person', home_department='Computer Science', also=['Mathematics'],
                 home_basis='primary_unresolved', primary_unresolved=['Computer Science', 'Mathematics'])]
    original = copy.deepcopy(rows)
    decision = dict(home_department='Artificial Intelligence', primary_stated=True,
                    home_department_evidence=_ev('School/Department: Artificial Intelligence'),
                    superseded_home_department='Computer Science',
                    why_superseded_home_department='Previous home was inferred incorrectly.')
    with pytest.raises(SystemExit, match='unresolved appointments'):
        apply_reviewed_homes(rows, {'A Person': decision}, lambda h: h)
    assert rows == original
