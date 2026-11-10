"""R-PAP-44 (owner-delegated 2026-11-09): title-only DBLP bindings need 10+ exact titles on one affiliated person, no namesake."""
import title_only_binding as t


def people(extra=None):
    p = {'p1': {'names': ['Bin Wang 0021'], 'keys': {f'k{i}' for i in range(12)}}}
    p.update(extra or {})
    return p


def test_R_PAP_44_ten_titles_one_person_accepted():
    assert t.decide({f'k{i}' for i in range(10)}, people(), 'p1', True) == (True, 'accepted')


def test_R_PAP_44_nine_titles_held():
    assert t.decide({f'k{i}' for i in range(9)}, people(), 'p1', True) == (False, 'fewer_than_10_exact_titles')


def test_R_PAP_44_titles_split_across_persons_held():
    ps = people()
    ps['p1']['keys'].discard('k3')
    assert t.decide({f'k{i}' for i in range(10)}, ps, 'p1', True)[1] == 'titles_not_all_on_one_person'


def test_R_PAP_44_no_affiliation_held():
    assert t.decide({f'k{i}' for i in range(10)}, people(), 'p1', False)[1] == 'no_school_affiliation'


def test_R_PAP_44_namesake_sharing_a_title_held():
    ps = people({'p2': {'names': ['Bin Wang 0044'], 'keys': {'k1'}}})
    assert t.decide({f'k{i}' for i in range(10)}, ps, 'p1', True)[1] == 'namesake_shares_matched_titles'


def test_R_PAP_44_other_name_sharing_coauthored_title_is_not_a_namesake():
    ps = people({'p2': {'names': ['Li Si'], 'keys': {'k1'}}})
    assert t.decide({f'k{i}' for i in range(10)}, ps, 'p1', True)[0]
