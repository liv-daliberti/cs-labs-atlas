import home_departments_school as H


def test_R_HOME_03_field_listing_never_sets_the_home():
    t = ['Associate Professor of Electrical and Computer Engineering', 'Computer Science', 'Faculty (Field) Computer Science']
    assert H.profile_home(t) == ('Electrical and Computer Engineering', [], 'listed_title')
    t = ['Associate Professor of Information Science', 'Information Science Computer Science', 'Faculty (Department) Information Science Faculty (Field) Computer Science']
    assert H.profile_home(t)[0::2] == ('Information Science', 'faculty_department')


def test_R_HOME_03_old_page_forms():
    assert H.profile_home(['Assistant Professor; Comp Biology, CS Field Member'])[0] == 'Comp Biology'
    assert H.profile_home(['Professor', 'ECE, CS Field Member'])[0] == 'ECE'
    assert H.profile_home(['Assistant Professor: ORIE; CS Field Member'])[0] == 'ORIE'
    assert H.profile_home(['Professor; Computer Science, Cornell Tech, CS Field Member']) == ('Computer Science', ['Cornell Tech'], 'listed_title')
    assert H.profile_home(['Professor, Mathematics', 'Computer Science', 'Faculty (Field) Computer Science'])[0] == 'Mathematics'


def test_R_HOME_03_unresolved_never_defaults_to_the_field():
    assert H.profile_home(['Provost', 'Computer Science', 'Faculty (Field) Computer Science']) == (None, [], 'primary_unresolved')


def test_R_HOME_03_rows_without_a_field_marker_are_untouched():
    assert H.profile_home(['Professor of Computer Science']) is None


def test_R_HOME_03_named_chair_is_not_a_unit():
    t = ['Laibe/Acheson Professor of Business Management & Leadership Studies', 'Computer Science', 'Faculty (Field) Computer Science']
    assert H.profile_home(t) == (None, [], 'primary_unresolved')
    t = ['Roxanne E. and Michael J. Zak Professor in Energy Systems Engineering', 'Faculty (Field) Computer Science']
    assert H.profile_home(t)[0] is None
    assert H.NAMED_CHAIR.search('Goenka Family Assistant Professor in Mathematics')
    assert not H.NAMED_CHAIR.search('Assistant Professor in Operations Research and Information Engineering')
