"""An open-ended 'PhD, 2024.9-' entry is a start year, still current (SJTU 马超 list, 2026-11-11)."""
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
