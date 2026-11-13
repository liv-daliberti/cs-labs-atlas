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


def test_own_school_degree_entry_reads_the_hkust_line_after_current_position():
    from labpage_audit import own_school_degree_entry
    t = ('Muleilan Pei Current position: TBC Thesis title: Learning to drive September 2021 - August 2026 The Hong Kong University of Science and Technology '
         'Ph.D. in Electronic and Computer Engineering September 2019 - August 2021 Harbin Institute of Technology M.Eng. in Control Science Research focus: Robot learning')
    rx = r'Hong Kong University of Science and Technology|HKUST'
    role, years, quote = own_school_degree_entry(t, 'Muleilan Pei', rx)
    assert (role, years) == ('phd', [2021, 2026]) and quote.endswith('Ph.D') and quote in t
    t2 = 'William Wu Current position: X September 2017 - August 2019 The Hong Kong University of Science and Technology M.Phil. in ECE'
    assert own_school_degree_entry(t2, 'William Wu', rx)[:2] == ('masters', [2017, 2019])
    assert own_school_degree_entry('Ann Lee Current position: X September 2017 - August 2019 Harbin Institute M.Eng.', 'Ann Lee', rx) is None
