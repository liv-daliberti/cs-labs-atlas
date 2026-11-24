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


def test_R_PAP_44_listing_linked_page_replaces_the_affiliation_note():
    page = {'url': 'https://www.cs.toronto.edu/~x/', 'sha256': 'ab' * 32}
    assert t.decide({f'k{i}' for i in range(10)}, people(), 'p1', False, page) == (True, 'accepted')


def test_R_PAP_44_listing_linked_page_needs_url_and_sha256():
    assert t.decide({f'k{i}' for i in range(10)}, people(), 'p1', False, {'url': 'https://x/'})[1] == 'no_school_affiliation'


def test_R_PAP_44_listing_linked_page_still_needs_ten_titles_and_no_namesake():
    page = {'url': 'https://x/', 'sha256': 'cd' * 32}
    assert t.decide({f'k{i}' for i in range(9)}, people(), 'p1', False, page)[1] == 'fewer_than_10_exact_titles'
    ps = people({'p2': {'names': ['Bin Wang 0044'], 'keys': {'k1'}}})
    assert t.decide({f'k{i}' for i in range(10)}, ps, 'p1', False, page)[1] == 'namesake_shares_matched_titles'


def test_R_PAP_44_person_name_must_equal_a_pi_alias():
    ten = {f'k{i}' for i in range(10)}
    ps = {'p1': {'names': ['Haibo Chen 0001'], 'keys': {f'k{i}' for i in range(12)}}}
    assert t.decide(ten, ps, 'p1', True, None, ['Rong Chen']) == (False, 'person_name_not_pi_alias')
    assert t.decide(ten, ps, 'p1', True, None, ['Haibo Chen'])[0]
    assert t.decide(ten, ps, 'p1', True, None, ['Chen, Haibo'.replace(',', '')])[0]   # word order ignored
    assert t.decide(ten, ps, 'p1', True)[0]   # no aliases passed: the old behavior


def test_R_PAP_44_hyphenated_alias_matches():
    ten = {f'k{i}' for i in range(10)}
    ps = {'p1': {'names': ['Wei-Long Zheng'], 'keys': {f'k{i}' for i in range(12)}}}
    assert t.decide(ten, ps, 'p1', True, None, ['Wei Long Zheng'])[0]
