from collections import Counter
from copy import deepcopy

from pihier.census import fold_dblp_ids, merge_census_rows


def test_rejected_resolver_pid_cannot_merge_susan_and_shawn_murphy():
    susan_pid = 'https://dblp.org/pid/05/3845'
    rows = [dict(name='Susan A Murphy', is_pi=True, dblp=[susan_pid],
                 collection_person_id='harvard_fac_susan-a-murphy'),
            dict(name='Shawn N. Murphy', is_pi=True, dblp=[],
                 collection_person_id='harvard_fac_shawn-n-murphy')]
    rows = fold_dblp_ids(rows, {'Shawn N. Murphy': {'pid': susan_pid}})
    before = deepcopy(rows)
    review = {'Shawn N. Murphy': {'dblp_drop': [susan_pid + '/']}}

    grouped, _ = merge_census_rows(rows, review, Counter())

    assert {tuple(r['name'] for r in group) for group in grouped.values()} == {
        ('Susan A Murphy',), ('Shawn N. Murphy',)}
    assert rows == before


def test_rejecting_one_pid_preserves_a_separate_valid_duplicate_anchor():
    rejected = 'https://dblp.org/pid/wrong'
    accepted = 'https://dblp.org/pid/owned'
    rows = [dict(name='Jessy Li', is_pi=True, dblp=[accepted]),
            dict(name='Junyi Jessy Li', is_pi=True, dblp=[rejected, accepted])]
    review = {'Junyi Jessy Li': {'dblp_drop': [rejected]}}

    grouped, _ = merge_census_rows(rows, review, Counter())

    assert len(grouped) == 1
    assert {r['name'] for r in next(iter(grouped.values()))} == {'Jessy Li', 'Junyi Jessy Li'}
