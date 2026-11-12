"""A combined MS/PhD heading does not establish each member's degree."""

from labpage_audit import entry_role, entry_years


def test_combined_degree_heading_leaves_role_unresolved():
    def role_of(_):
        return 'phd', None

    assert entry_role('', 'Advisees > MS/PhD students', role_of) == (
        None, 'mixed_degree_section_heading')
    assert entry_role('(PhD student)', 'Advisees > MS/PhD students', role_of) == (
        'phd', 'entry')


def test_double_hyphen_alumni_year_range():
    assert entry_years('B.S., Computer Science, 2021--2022, BoolODE',
                       'Former undergraduate students') == ([2021, 2022], 'stated_in_entry')
