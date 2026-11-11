"""An open-ended 'PhD, 2024.9-' entry is a start year, still current (SJTU 马超 list, 2026-11-11)."""
import re
import labpage_audit as L


def test_open_ended_month_ranges_are_a_start_and_stay_current():
    for d in ('PhD, 2024.9-', 'PhD, 2024.9–', 'PhD, 2024.9至今', 'PhD student 2024/09 - present', 'PhD 2024.09 to present'):
        years, basis = L.entry_years(d, None)
        assert years == [2024, None] and basis == 'stated_in_entry', d
        assert not L.entry_years_end_the_stay(years, basis)


def test_closed_and_degree_year_entries_are_unchanged():
    assert L.entry_years('(Postdoc, 2010-2014)', None)[0] == [2010, 2014]
    assert L.entry_years('PhD 2021', None)[0] == [None, 2021]


def test_bare_degree_year_in_a_current_list_is_an_entry_year():
    for d in ('(Ph.D./M.S. 2023)', 'Ph.D. 2023', '(Ph.D. 2023)'):
        assert L.entry_years(d, 'Current Students')[0] == [2023, None], d
        assert not L.entry_years_end_the_stay(*L.entry_years(d, 'Current Students'))
    # outside a current list, or in a mixed / alumni heading, a degree year still ends the stay
    assert L.entry_years('Ph.D. 2023', 'Alumni')[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2023', 'Current and Former Students')[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2023', None)[0] == [None, 2023]
    assert L.entry_years('Ph.D. 2019-2023', 'Current Students')[0] == [2019, 2023]


def test_slash_date_open_start_and_prior_degree_after_from_is_not_the_role():
    for d in ('Ph.D student, 2022/9/1 to present; B.S. from X', 'Ph.D student, 2022/9/1 - present. B.S. from X', 'Ph.D student 2022/9/1–'):
        assert L.entry_years(d, None) == ([2022, None], 'stated_in_entry'), d
    ro = lambda t: ('phd' if re.search(r'ph\.?\s?d', t, re.I) else 'undergraduate' if re.search(r'\bb\.?s\.?\b', t, re.I) else None, 'x')
    assert L.entry_role('Ph.D student, 2022/9/1 to present; B.S. from Tsinghua University', 'Members', ro)[0] == 'phd'
    assert L.entry_role('Ph.D student, 2022/9/1 to present', 'Members', ro)[0] == 'phd'


def test_incoming_joint_institute_unclosed_bracket_and_bare_year_under_group_heading():
    assert L.incoming_entry('incoming Ph.D. (Fall 2027)', '') and L.incoming_entry('(2027)', '') and L.incoming_entry('admitted for 2027', '')
    assert not L.incoming_entry('Ph.D. student, 2024-', '')
    assert L.joint_other_institute_entry('Co-supervised by Prof. Li, Shanghai AI Laboratory', '', 'sjtu')
    assert L.joint_other_institute_entry('joint PhD with Shanghai Innovation Institute', '', 'sjtu')
    assert not L.joint_other_institute_entry('Ph.D. student, 2023-', '', 'sjtu')
    assert L.clean_parenthetical_name('Haolan Zhang（Ph.D') == ('Haolan Zhang', 'phd')
    assert L.clean_parenthetical_name('Ann Lee (PhD') == ('Ann Lee', 'phd')
    assert L.entry_years('(Ph.D./M.S. 2023)', 'Research Group Graduate Students')[0] == [2023, None]
    assert L.entry_years('M.S. 2026', 'Research Group Graduate Students')[0] == [2026, None]
    assert L.entry_years('Ph.D. 2023', 'Graduated Students')[0] == [None, 2023]


def test_sjtu_round6_parse_items_from_the_stored_pages():
    ro = lambda t: ('phd' if re.search(r'ph\.?\s?d', t, re.I) else 'masters' if re.search(r'master', t, re.I) else 'undergraduate' if re.search(r'\bb\.?s\.?\b|undergrad', t, re.I) else 'member', 'x')
    # year after award brackets is the entry year (马叶涵's page)
    assert L.entry_years('(2024 Zhongyuan Scholarship, 2025 Huawei Scholarship) 2022', 'Graduate Students')[0] == [2022, None]
    assert L.entry_years('(2026 National Scholarship) 2024 Yiming Zhang', 'Graduate Students > 2025')[0] == [2024, None]
    # dates in the bracket after a co-advised bracket (郑臻哲's page); the B.S. held on arrival is not the role
    d = '(Co-Advised with Prof. Guihai Chen) (2020-, B.S. CS@ Shanghai Jiao Tong University)'
    assert L.entry_years(d, 'Ph.D. students')[0] == [2020, None]
    assert L.entry_role(d, 'Ph.D. students', ro)[0] == 'phd'
    # a Chinese name token before the role (Jia Xiang on 陈国兴's page)
    assert L.entry_role('(向嘉 Master Student, 2021-2024, Alibaba Cloud)', 'Alumni', ro)[0] == 'masters'
    # visit ranges (ZJU 沈春华's visitors)
    assert L.entry_years('2019 ↝ 2020 Visit', None)[0] == [2019, 2020]
    assert L.entry_years('(2019-20 Visit)', None)[0] == [2019, 2020]
    assert L.entry_years('2019-20 Visit', None)[0] == [2019, 2020]
