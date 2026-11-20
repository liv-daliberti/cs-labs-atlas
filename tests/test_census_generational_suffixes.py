from collections import Counter

from pihier.census import merge_census_rows


def test_same_given_name_and_suffix_do_not_merge_different_surnames():
    rows = [dict(name=name, is_pi=True) for name in
            ['Earl E. Swartzlander Jr.', 'Earl W. Huff Jr.']]
    merged, nicknames = merge_census_rows(rows, {}, Counter())
    assert len(merged) == 2
    assert nicknames == []


def test_suffix_and_nickname_variants_still_merge_same_person():
    rows = [dict(name=name, is_pi=True) for name in
            ['Robert A. Jones Jr.', 'Bob Jones']]
    merged, _ = merge_census_rows(rows, {}, Counter())
    assert len(merged) == 1


def test_explicit_person_anchor_is_preserved_across_different_name_forms():
    rows = [dict(name=name, is_pi=True, collection_person_id='same-person')
            for name in ['Earl E. Swartzlander Jr.', 'Earl Swartzlander']]
    merged, _ = merge_census_rows(rows, {}, Counter())
    assert len(merged) == 1
