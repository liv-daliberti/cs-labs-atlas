"""Stanford round-7 repairs (2026-11-11): Contact-block administrators, collaborators in prose, co-chairs, possessive title fragments,
a maintained page with an old copyright footer, and a pipe table whose first row has no leading pipe."""
import labpage_audit as L


def test_contact_block_names_are_staff():
    # profiles.stanford.edu: the degree line above the block read it as a PhD section (Pavone, Demszky, Hinds, Wong)
    assert L.admin_staff_entry('Ph.D., MIT, Aeronautics and Astronautics (2010) > Contact', '', 'Contact Administrator Renee Quiroz')
    assert L.admin_staff_entry('Professional Education PhD, Lehigh (1988) > Contact > Alternate Contact', '', 'Alternate Contact Isabelle London')
    assert L.admin_staff_entry('x', '', 'Tel: (650) 723-4432 Administrator Carolyn Edwards')
    assert L.admin_staff_entry('x', '', 'Contact Admin. Support Melissa Cromosini')
    assert not L.admin_staff_entry('Stanford Advisees', 'Doctoral', 'Stanford Advisees Pu Deng')
    assert not L.admin_staff_entry('Contact', 'PhD student', 'Contact Jo Li')


def test_collaborators_and_chairs_are_not_members():
    assert L.prose_nonmember('Vahideh Manshadi', '', 'Ross Anderson (at Google) I also worked with Vahideh Manshadi')
    assert L.prose_nonmember('Lyn Frazier', ' co-chair)', 'Jesse A. Harris (2012, UMass; Lyn Frazier')
    assert not L.prose_nonmember('Ana Klimovic', ' (EE, PhD', 'Current Students Ana Klimovic')


def test_possessive_title_fragment_is_not_a_name():
    assert L.nonmember_candidate("Clifford's Geometric Algebra", 'Alumni')
    assert not L.nonmember_candidate("Conor O'Brien", 'Alumni')


def test_footer_year_alone_does_not_make_a_maintained_page_stale():
    assert L.stale_footer_year('Copyright 2008 ... PhD students 2016-2018 Ana Klimovic', 2026) is None
    assert L.stale_footer_year('Copyright 2012 ... students 2010 2011', 2024) == 2012


def test_pipe_table_year_after_the_name_without_leading_pipe():
    assert L.entry_years('Texas A&M | 1989 | Richard Chappell | Univ. of Wisconsin-Madison | 1990', 'Students') == ([None, 1989], 'stated_in_entry')


def test_clinical_professor_title_is_faculty():
    assert L.PROF_TITLE_DESC.search('(Clinical Assistant Professor of Pediatrics)')
