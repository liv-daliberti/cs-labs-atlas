"""An unknown listing year is a discovery hint, never an edition date."""
from labpage_recover import Index, appointment, in_window


def candidate(year):
    return dict(ct='atitleforapaper', cite=['atitleforapaper'], year=year)


def test_undated_listing_can_match_exact_dated_metadata():
    index = Index([candidate(0), candidate(2022)])
    assert index.match('atitleforapaper', 2019) == {0: 'exact_title'}
    assert index.match('atitleforapaper', 2022) == {0: 'exact_title', 1: 'exact_title'}


def test_unknown_listing_year_does_not_supply_edition_eligibility():
    assert not in_window(0)
    assert appointment(dict(periods=[], listings=[]), 0) is None
    assert not in_window(2015)
    assert appointment(dict(periods=[], listings=[]), 2021) is None
