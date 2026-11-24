"""Reviewed per-link exclusions: one candidate student-paper link is removed, the rest stay; invalid input stops the build."""
import pytest
from pihier import links


def sp(pi, name, oa):
    return dict(pi=pi, student='s:' + name, name=name, oa=oa, status='candidate', basis='x')


def test_exclusion_removes_only_that_link():
    rows = [sp('P', 'A B', 'W1'), sp('P', 'A B', 'W2'), sp('P', 'C D', 'W1')]
    doc = {'version': 1, 'school': 'x', 'exclusions': [dict(pi='P', student='A B', oa='W1', why='unlabelled roster')]}
    kept, excluded, unmatched = links.exclude_links(rows, doc)
    assert [(r['name'], r['oa']) for r in kept] == [('A B', 'W2'), ('C D', 'W1')]
    assert (excluded, unmatched) == (1, 0)


def test_unmatched_exclusion_is_counted_not_fatal():
    kept, excluded, unmatched = links.exclude_links([sp('P', 'A B', 'W1')], {'exclusions': [dict(pi='P', student='Z', oa='W9', why='w')]})
    assert len(kept) == 1 and (excluded, unmatched) == (0, 1)


def test_exclusion_without_a_reason_is_refused():
    with pytest.raises(ValueError):
        links.exclude_links([], {'exclusions': [dict(pi='P', student='A', oa='W1')]})
