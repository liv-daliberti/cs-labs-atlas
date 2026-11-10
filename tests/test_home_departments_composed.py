"""Composed-school home departments: a center is never a home, a single listed unit is, a reviewed decision needs sourced evidence."""
import pytest

import home_departments_composed as H

U = {'CADCG': 'State Key Laboratory of CAD&CG', 'ICSR': 'Institute of Cyberspace Security Research', 'CS_MAIN': 'Main College of Computer Science'}
B = dict(url='https://x', sha256='a' * 64, quote='q')


def row(name, codes):
    return dict(name=name, is_pi=True, departments=codes, pi_basis=B)


def test_center_only_pi_is_held_and_single_unit_listed():
    out = {r['name']: r for r in H.build([row('A', ['CADCG']), row('B', ['ICSR'])], {}, U, {'CADCG'})}
    assert out['A']['status'] == 'hold' and out['A']['home_department'] is None
    assert out['B']['status'] == 'accepted' and out['B']['home_basis'] == 'listed_title'


def test_reviewed_primary_unresolved_keeps_every_unit():
    ev = [dict(B)]
    dec = {'A': dict(home_department='Main College of Computer Science', home_department_evidence=ev,
                     primary_unresolved=['Main College of Computer Science', 'State Key Laboratory of CAD&CG'])}
    r = H.build([row('A', ['CADCG'])], dec, U, {'CADCG'})[0]
    assert r['home_basis'] == 'primary_unresolved' and 'State Key Laboratory of CAD&CG' in r['also'] and r['status'] == 'accepted'


def test_reviewed_home_needs_evidence_and_two_units():
    with pytest.raises(SystemExit):
        H.build([row('A', ['CADCG'])], {'A': dict(home_department='X')}, U, set())
    with pytest.raises(SystemExit):
        H.build([row('A', ['CADCG'])], {'A': dict(home_department='X', home_department_evidence=[B], primary_unresolved=['X'])}, U, set())
