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


def test_innermost_bare_degree_heading_wins_over_outer_heading():
    def role_of(text):
        return ('phd', None) if 'phd' in (text or '').lower() else (None, None)

    assert entry_role('Bowen Zhu (co-supervised, 2023-)', 'Phd > Master', role_of) == ('masters', 'section_heading')
    assert entry_role('Runpei Cai (co-supervised, 2024-)', 'Phd', role_of) == ('phd', 'section_heading')


def test_started_term_is_an_open_start():
    assert entry_years("(started F'2022)", 'Current Students') == ([2022, None], 'stated_in_entry')
    assert entry_years('(started Fall 2025) Co-advised with X', 'Students') == ([2025, None], 'stated_in_entry')
    assert entry_years("(started S'23)", 'Students') == ([2023, None], 'stated_in_entry')


def test_a_stay_range_after_the_name_is_not_a_news_line():
    from labpage_audit import news_item
    assert not news_item('Zhe Tong 佟哲 September 2026 - Present B.Eng., HKUST Research focus: Robotics')
    assert not news_item('Yang Xu September 2024 - December 2025 M.Eng.')
    assert news_item('August 2025: Patrick Kastner and I just received a seed grant')
    assert news_item('August 2025 - I gave a talk with Ann Lee at X')
