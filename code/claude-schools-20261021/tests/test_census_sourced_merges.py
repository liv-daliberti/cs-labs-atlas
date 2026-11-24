from collections import Counter

import pytest

from pihier.census import merge_census_rows


def review(canonical, alias):
    return dict(canonical=canonical, aliases=[alias], reviewed_by='source-reviewer',
                why='The official biography explicitly identifies both names as one person.',
                evidence=[dict(url='https://university.example/faculty', sha256='a' * 64,
                               quote=f'{canonical}, also known as {alias}')])


def test_sourced_merge_keeps_explicit_canonical_name_even_when_it_occurs_later():
    rows = [dict(name='Jessy Li', is_pi=True, sources=['cs-roster']),
            dict(name='Junyi Jessy Li', is_pi=True, sources=['linguistics-roster'])]
    grouped, _ = merge_census_rows(rows, {}, Counter(), [review('Junyi Jessy Li', 'Jessy Li')])
    assert len(grouped) == 1
    group = next(iter(grouped.values()))
    assert group[0]['name'] == 'Junyi Jessy Li'
    assert {x['name'] for x in group} == {'Jessy Li', 'Junyi Jessy Li'}
    assert {s for x in group for s in x['sources']} == {'cs-roster', 'linguistics-roster'}


def test_different_given_names_are_not_merged_without_explicit_source_review():
    rows = [dict(name=name, is_pi=True) for name in ['Al Mok', 'Aloysius K. Mok']]
    assert len(merge_census_rows(rows, {}, Counter())[0]) == 2
    assert len(merge_census_rows(rows, {}, Counter(), [review('Aloysius K. Mok', 'Al Mok')])[0]) == 1


def test_unsourced_or_overlapping_merge_reviews_fail_before_grouping():
    rows = [dict(name=name, is_pi=True) for name in ['Jessy Li', 'Junyi Jessy Li']]
    bad = review('Junyi Jessy Li', 'Jessy Li')
    bad['evidence'] = []
    with pytest.raises(ValueError, match='source evidence'):
        merge_census_rows(rows, {}, Counter(), [bad])
    with pytest.raises(ValueError, match='overlapping'):
        merge_census_rows(rows, {}, Counter(), [review('Junyi Jessy Li', 'Jessy Li'),
                                               review('Jessy Li', 'Junyi Jessy Li')])
