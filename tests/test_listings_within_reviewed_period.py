import pytest

from pihier.periods import drop_listings_outside_periods

REVIEW = {'why': 'only proven years', 'evidence': [{'url': 'u', 'sha256': 'a' * 64, 'quote': 'q'}]}
L = {y: {'year': y} for y in (2016, 2017, 2020, 2022, 2026)}


def test_years_outside_the_reviewed_period_are_dropped():
    kept, dropped = drop_listings_outside_periods(L, [{'start': '2019', 'end': '2022'}], REVIEW, 'X')
    assert sorted(kept) == [2020, 2022] and dropped == [2016, 2017, 2026]


def test_no_override_changes_nothing():
    assert drop_listings_outside_periods(L, [{'start': '2019', 'end': '2022'}], None) == (L, [])


def test_override_needs_reason_evidence_and_a_period():
    with pytest.raises(ValueError):
        drop_listings_outside_periods(L, [{'start': '2019', 'end': '2022'}], {'why': 'x', 'evidence': []}, 'X')
    with pytest.raises(ValueError):
        drop_listings_outside_periods(L, [], REVIEW, 'X')
