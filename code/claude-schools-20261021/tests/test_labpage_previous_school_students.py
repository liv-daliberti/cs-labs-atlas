"""Princeton acceptance round 4: students of the institution a PI moved from, listed on the PI's mixed page, are not this school's members."""
import labpage_audit as A


def test_foreign_degree_label_places_an_alumnus_at_the_previous_school():
    # Ben Raphael's Princeton page: 'Ashley Conard (Sc.M. Computational Biology and Computer Science 2018) -> Ph.D. student, Brown University'
    assert A.foreign_degree_entry('(Sc.M. Computational Biology and Computer Science 2018) → Ph.D. student, Brown University', 'princeton')
    assert A.foreign_degree_entry('Sc.M. 2016', 'princeton') and A.foreign_degree_entry('ScB 2012', 'mit')


def test_foreign_degree_label_is_not_read_in_a_destination_or_at_its_own_owner():
    assert not A.foreign_degree_entry('(M.S.E. 2019) → Sc.M. student, Brown University', 'princeton')   # the arrow's right side is a destination
    assert not A.foreign_degree_entry('Sc.M. 2016', 'brown')
    assert not A.foreign_degree_entry('(Ph.D. 2019) → Google', 'princeton') and not A.foreign_degree_entry(None, 'princeton')


def test_heading_naming_another_institution_places_the_list_there():
    assert A.other_institution_heading('Alumni > Brown University alumni', 'princeton') == 'Brown University'
    assert A.other_institution_heading('Members > At Brown: former students', 'princeton') == 'Brown'
    assert A.other_institution_heading('Students at Rice University', 'princeton') == 'Rice University'


def test_heading_naming_this_school_or_a_plain_roster_stays_a_roster():
    assert not A.other_institution_heading('Alumni > Princeton University alumni', 'princeton')
    assert not A.other_institution_heading('Alumni > Ph.D. Students', 'princeton')
    assert not A.other_institution_heading('Master’s Students', 'princeton') and not A.other_institution_heading(None, 'princeton')
    assert not A.other_institution_heading('Current Position', 'princeton') and not A.other_institution_heading('Brown University > Princeton University alumni', 'princeton')


def test_princeton_a_b_degree_line_is_a_degree_origin_not_a_location():
    # Houck's roster gives each member's earlier degrees ('A.B. Physics, Dartmouth College (2022)'): where the degree came from, not where the person is (Princeton A.B. = bachelor of arts)
    assert not A.other_institution_entry('A.B. Physics, Dartmouth College (2022) Email', 'A.B. Physics, Dartmouth College (2022) Email', 'princeton')
    assert A.other_institution_entry('Graduate student, Physics@Dartmouth College, 2019 - 2022', '', 'princeton')


def test_year_heading_under_current_students_is_an_expected_completion_not_a_start():
    # dbertsim.mit.edu/students: 'Current Students > 2027' lists 'Jiayi Gu / Expected completion': read as [2027, 2027] it was dropped as an incoming student (15 current PhD students)
    assert A.entry_years('Expected completion', 'Current Students > 2027') == (None, 'none')
    assert A.entry_years('', 'Current Students > 2030') == (None, 'none')
    # a year heading of a past list is still that year, and a current list's year heading at or before this year without 'expected' keeps its reading
    assert A.entry_years('', 'Past Students > 2019') == ([2019, 2019], 'section_year_heading')
    assert A.entry_years('', 'Members > 2019') == ([2019, 2019], 'section_year_heading')
