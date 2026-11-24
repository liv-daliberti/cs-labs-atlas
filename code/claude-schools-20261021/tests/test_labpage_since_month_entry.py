"""NTU Long Cheng's team page: 'since MM/YYYY' entries (2026-11-14)."""

from labpage_audit import entry_years, nearer_nonphd_heading, trim_merged_since_entry


def test_since_month_year_is_an_open_start_and_a_merged_entry_reads_its_own_date():
    assert entry_years('since 08/2024', 'Current members > PhD students') == ([2024, None], 'stated_in_entry')
    assert entry_years('since 08/2022 Xi YUAN since 08/2023', 'PhD students') == ([2022, None], 'stated_in_entry')
    assert entry_years('Kethmi HETTIGE since 13/2024', 'PhD students')[0] != [2024, None]   # not a month


PAGE = ('PhD students Jane DOE since 01/2025 Research fellows Ann LEE 2019 - 2020 Master\'s students Jane DOE '
        'Now: PhD student in our group 2023 - 2024 Visiting students Bob ROE')


def test_a_master_stage_entry_that_says_now_phd_does_not_withhold_the_phd_role():
    assert nearer_nonphd_heading(PAGE, 'Jane DOE', 'PhD students') is False
    other = PAGE.replace('Now: PhD student in our group', 'Now: Engineer at X')
    assert nearer_nonphd_heading(other, 'Jane DOE', 'PhD students') is True      # a mixed list still withholds


def test_a_merged_since_entry_is_trimmed_to_its_own_date():
    assert trim_merged_since_entry('since 08/2022 Xi YUAN since 08/2022') == 'since 08/2022'
    assert trim_merged_since_entry('since 08/2022') == 'since 08/2022'
    assert trim_merged_since_entry('PhD student, since 2022 Xi YUAN since 2023') == 'PhD student, since 2022 Xi YUAN since 2023'
