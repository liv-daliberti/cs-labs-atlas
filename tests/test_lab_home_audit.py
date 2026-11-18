import lab_home_audit as A


EV = dict(url='https://example.edu/faculty', sha256='a' * 64, quote='Ann, Professor')
CFG = dict(departments=[dict(code='CS', name='Computer Science')], affiliated_units=[], census={})


def test_department_code_aliases_do_not_create_false_conflicts():
    shared = dict(status='accepted', home_department='Department of Computer Science', evidence=EV, home_basis='listed_title')
    local = dict(status='accepted', home_department='CS', evidence=EV, home_basis='listed_title')
    assert A.assess(local, shared, local, CFG, {}) == []


def test_missing_and_ambiguous_homes_cannot_receive_clear_status():
    assert A.assess(None, None, None, CFG, {}) == ['missing_home']
    row = dict(status='accepted', home_department='CS', home_basis='primary_unresolved', evidence=EV)
    assert A.assess(row, None, row, CFG, {}) == ['primary_unresolved']


def test_single_unit_proposal_requires_same_unit_captured_listing():
    pi = dict(departments=['CS'], rank='ladder', listings=[dict(EV, kind='dept_listing:CS', year=2025)])
    assert A.proposed_from_listing(pi, CFG)['home_department'] == 'Computer Science'
    assert A.proposed_from_listing(dict(pi, departments=['CS', 'STAT']), CFG) is None
    assert A.proposed_from_listing(dict(pi, listings=[dict(EV, kind='unit_listing:ML', year=2025)]), CFG) is None
    assert A.proposed_from_listing(dict(pi, rank='courtesy'), CFG) is None
