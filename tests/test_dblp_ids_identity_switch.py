import dblp_ids_school as D

KR = {'name_only': 'propose', 'common_surnames': ['kim', 'lee', 'yoon', 'han']}


def test_stock_schools_bind_every_rule():
    for basis in ('homepage_url', 'school_affiliation', 'school_coauthors', 'unique_name', 'unique_exact_name'):
        assert D.identity_binds({}, 'Jane Kim', [], basis)
        assert D.identity_binds(None, 'Jane Kim', [], basis)


def test_propose_switch_never_binds_name_only_rules():
    for basis in ('unique_name', 'unique_exact_name'):
        assert not D.identity_binds(KR, 'Taisook Han', [], basis) and not D.identity_binds(KR, 'Martin Ziegler', [], basis)


def test_common_surname_binds_only_on_an_identifier():
    assert D.identity_binds(KR, 'Taisook Han', [], 'homepage_url')
    for basis in ('school_affiliation', 'school_coauthors'):
        assert not D.identity_binds(KR, 'Moonzoo Kim', [], basis)
        assert not D.identity_binds(KR, 'Sung-Eui Yoon', ['Sungeui Yoon'], basis)
        assert D.identity_binds(KR, 'Martin Ziegler', [], basis)     # a rare surname with a KAIST note and no namesake still binds


def test_family_first_and_comma_forms_and_the_wider_surname_list():
    wide = {'name_only': 'propose', 'common_surnames': ['kim', 'jang', 'chang', 'hwang', 'kwon', 'heo', 'huh', 'baek']}
    for nm in ('Kim Jaechul', 'KIM Joo-Young', 'Kim, Jaechul', 'Jaechul Kim', 'Joo-Young KIM'):
        assert not D.identity_binds(wide, nm, [], 'school_affiliation'), nm
        assert not D.identity_binds(wide, nm, [], 'school_coauthors'), nm
        assert D.identity_binds(wide, nm, [], 'homepage_url')
    for nm in ('Heo, Kihong', 'Kihong Heo', 'Hwang Sungjin', 'Jang, Youngjae', 'Kwon Seokbeom'):
        assert not D.identity_binds(wide, nm, [], 'school_affiliation'), nm
    assert D.identity_binds(wide, 'Martin Ziegler', [], 'school_affiliation')
