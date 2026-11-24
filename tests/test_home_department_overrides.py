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


@pytest.mark.parametrize('primary_stated', [True, False])
def test_resolving_a_primary_clears_the_old_candidates_and_keeps_affiliations(primary_stated):
    from home_department_registry import review

    rows = [dict(name='A Person', home_department='Computer Science', also=['Research Lab'],
                 status='accepted', home_basis='primary_unresolved',
                 primary_unresolved=['Computer Science', 'Statistics', 'Electrical Engineering'])]
    decision = dict(home_department='Statistics', primary_stated=primary_stated,
                    primary_unresolved=[], home_department_evidence=_ev('Primary department: Statistics'))
    row = apply_reviewed_homes(rows, {'A Person': decision}, lambda h: h)[0]
    assert not row.get('primary_unresolved')
    assert row['home_basis'] == ('primary_stated' if primary_stated else 'listed_title')
    assert review(row)['primary_resolved']
    assert set(row['also']) == {'Computer Science', 'Electrical Engineering', 'Research Lab'}
    # Reapplying the same sourced decision cannot restore the former ambiguity.
    assert apply_reviewed_homes(copy.deepcopy(rows), {'A Person': decision}, lambda h: h) == rows


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


def test_reviewed_non_pi_faculty_home_survives_rebuild_without_admitting_a_pi(monkeypatch, tmp_path):
    import json
    import atlas_paths as P
    import census_overrides as CO
    import home_departments_school as H

    cfg = {'departments': [], 'affiliated_units': [], 'census': {}}
    faculty = [dict(name='Reviewed Instructor', is_pi=False, rank='teaching'),
               dict(name='Unreviewed Instructor', is_pi=False, rank='teaching')]
    original = copy.deepcopy(faculty)
    census = tmp_path / 'census-faculty.json'
    census.write_text(json.dumps({'faculty': faculty}))
    (tmp_path / 'rows.json').write_text('[]')
    decision = dict(home_department='Information Sciences',
                    home_department_evidence=_ev('Reviewed Instructor, Teaching Professor, Information Sciences'))
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(P, 'data', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(P, 'data_w', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(CO, 'section', lambda key: {'Reviewed Instructor': decision})

    H.main('uiuc')
    path = tmp_path / 'home-departments-school.json'
    rows = json.loads(path.read_text())
    assert [row['name'] for row in rows] == ['Reviewed Instructor']
    assert rows[0]['status'] == 'accepted'
    assert rows[0]['home_department'] == 'Information Sciences'
    assert rows[0]['faculty_only_record']
    assert json.loads(census.read_text())['faculty'] == original
    H.main('uiuc')
    assert json.loads(path.read_text()) == rows


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


def test_documented_research_unit_exception_survives_sourced_reapplication():
    from census_overrides import HOME_FIELDS

    assert 'no_academic_department' in HOME_FIELDS
    rows = [dict(name='Institute Researcher', home_department=None, also=[], status='hold',
                 no_academic_department=False)]
    decision = dict(home_department='Information Trust Institute', no_academic_department=True,
                    home_department_evidence=_ev('Institute Researcher, Research Professor, Information Trust Institute'))
    apply_reviewed_homes(rows, {'Institute Researcher': decision}, lambda h: h)
    assert rows[0]['status'] == 'accepted'
    assert rows[0]['no_academic_department'] is True
    assert apply_reviewed_homes(copy.deepcopy(rows), {'Institute Researcher': decision}, lambda h: h) == rows


def test_reviewed_home_does_not_retain_a_campus_discovery_roster_as_a_department(monkeypatch, tmp_path):
    import json
    import atlas_paths as P
    import census_overrides as CO
    import home_departments_school as H

    cfg = {'departments': [], 'affiliated_units': [dict(
        code='CAMPUS', name='Campus-wide faculty directory (candidate discovery only)')], 'census': {}}
    for name, value in {'census-faculty.json': {'faculty': []}, 'rows.json': [],
                        'census-additions.json': [dict(name='Campus Professor', is_pi=True,
                                                      departments=['CAMPUS'])]}.items():
        (tmp_path / name).write_text(json.dumps(value))
    decision = dict(home_department='Statistics',
                    home_department_evidence=_ev('Campus Professor, Professor, Statistics'))
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(P, 'data', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(P, 'data_w', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(CO, 'section', lambda key: {'Campus Professor': decision})
    H.main('uiuc')
    row = json.loads((tmp_path / 'home-departments-school.json').read_text())[0]
    assert row['home_department'] == 'Statistics'
    assert row['also'] == []


@pytest.mark.parametrize('basis, kind', [('first_listed_site', 'faculty_owned_site'),
                                         ('first_listed_publication', 'authored_publication')])
def test_R_HOME_02_first_listed_home_is_distinct_from_stated_primary_and_retains_joint_units(basis, kind):
    from home_department_registry import review

    rows = [dict(name='Joint Professor', home_department='Statistics', also=['Research Institute'],
                 primary_unresolved=['Statistics', 'Computer Science'], home_basis='primary_unresolved')]
    ev = _ev('Joint Professor, Computer Science and Statistics')
    ev[0].update(kind=kind, ordered_departments=['Computer Science', 'Statistics'])
    decision = dict(home_department='Computer Science', primary_stated=False, primary_unresolved=[],
                    home_selection_basis=basis, home_department_evidence=ev)
    row = apply_reviewed_homes(rows, {'Joint Professor': decision}, lambda u: u)[0]
    assert row['home_basis'] == basis
    assert row['home_selection_basis'] == basis
    assert set(row['also']) == {'Statistics', 'Research Institute'}
    assert not row.get('primary_unresolved')
    assert review(row)['primary_resolved']
    assert not review(row)['primary_stated']
    assert apply_reviewed_homes(copy.deepcopy(rows), {'Joint Professor': decision}, lambda u: u) == rows


@pytest.mark.parametrize('change', [dict(home_department='Statistics'), dict(primary_stated=True),
                                   dict(primary_unresolved=['Computer Science', 'Statistics']),
                                   dict(home_selection_basis='alphabetical')])
def test_first_listed_home_rejects_unmatched_order_and_false_primary(change):
    ev = _ev('Joint Professor, Computer Science and Statistics')
    ev[0].update(kind='faculty_owned_site', ordered_departments=['Computer Science', 'Statistics'])
    decision = dict(home_department='Computer Science', home_selection_basis='first_listed_site',
                    home_department_evidence=ev) | change
    with pytest.raises(SystemExit, match='first-listed selection'):
        apply_reviewed_homes([dict(name='Joint Professor')], {'Joint Professor': decision}, lambda u: u)


def test_current_non_pi_and_historical_pi_share_one_home_and_accepted_aliases_do_not_duplicate_it(monkeypatch, tmp_path):
    import json
    import atlas_paths as P
    import census_overrides as CO
    import home_departments_school as H

    cfg = {'departments': [], 'affiliated_units': [], 'census': {}}
    faculty = [dict(name='Current Adjunct', is_pi=False), dict(name='Canonical Professor', is_pi=True)]
    additions = [dict(name='Current Adjunct', is_pi=True), dict(name='Accepted Alias', is_pi=True)]
    pis = [dict(pi='Current Adjunct', names=['Current Adjunct']),
           dict(pi='Canonical Professor', names=['Canonical Professor', 'Accepted Alias'])]
    for name, value in {'census-faculty.json': {'faculty': faculty}, 'rows.json': [],
                        'census-additions.json': additions, 'pis.json': pis}.items():
        (tmp_path / name).write_text(json.dumps(value))
    reviewed = {p['pi']: dict(home_department='Information Sciences',
                             home_department_evidence=_ev(p['pi'] + ', Information Sciences')) for p in pis}
    monkeypatch.setattr(H.S, 'get', lambda key: cfg)
    monkeypatch.setattr(P, 'data', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(P, 'data_w', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(CO, 'section', lambda key: reviewed)
    H.main('uiuc')
    rows = json.loads((tmp_path / 'home-departments-school.json').read_text())
    assert len(rows) == 2
    assert {r['name'] for r in rows} == {p['pi'] for p in pis}
    assert not any(r.get('faculty_only_record') for r in rows)
    assert json.loads((tmp_path / 'pis.json').read_text()) == pis
    assert json.loads((tmp_path / 'census-faculty.json').read_text())['faculty'] == faculty


def test_later_explicit_primary_supersedes_first_listed_basis_without_losing_other_units():
    from home_department_registry import review

    rows = [dict(name='Joint Professor', home_department='Computer Science', also=['Statistics'],
                 home_basis='first_listed_site', home_selection_basis='first_listed_site', status='accepted')]
    decision = dict(home_department='Statistics', primary_stated=True,
                    home_department_evidence=_ev('Primary appointment: Statistics'))
    row = apply_reviewed_homes(rows, {'Joint Professor': decision}, lambda u: u)[0]
    assert row['home_basis'] == 'primary_stated'
    assert 'home_selection_basis' not in row
    assert row['also'] == ['Computer Science']
    assert review(row)['primary_stated']
