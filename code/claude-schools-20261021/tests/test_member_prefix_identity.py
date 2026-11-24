"""Distinct roster cards must not collapse merely because East Asian given names share a prefix."""
from collections import Counter
from types import SimpleNamespace

import pytest

from pihier.names import Name, same_student
from pihier.students import merge_within_lab


@pytest.mark.parametrize('a,b', [('Jiali Li', 'Jialin Li'), ('Xiao Liu', 'Xiaoyuan Liu'),
                               ('Seung Lee', 'Seunghak Lee'), ('Jun Zhu', 'Junyan Zhu')])
def test_distinct_given_names_under_east_asian_family_are_not_prefix_aliases(a, b):
    assert not Name([a]).match(b)
    assert not same_student(a, b)
    assert not same_student(b, a)


def test_two_separately_named_pacman_postdoc_cards_survive_native_merge():
    ctx = SimpleNamespace(pis=[dict(pi='Example PI')], n=Counter(), initials_merges=[])
    base = 'https://pacman.cs.tsinghua.edu.cn/~zjd/'
    records = {}
    for slug, name in [('jiali-li', 'Jiali Li'), ('jialin-li', 'Jialin Li')]:
        records[slug] = dict(person=slug, name=name, roles=['postdoc'], relations=[dict(
            type='researched_membership', role='postdoc', years=[2026],
            sources=[dict(url=base + 'people/', quote=name + ' Postdoc', member_profile=base + 'author/' + slug + '/')])])
    stu = {'Example PI': records}
    assert merge_within_lab(ctx, stu) == 0
    assert {r['name'] for r in stu['Example PI'].values()} == {'Jiali Li', 'Jialin Li'}
    assert all(not r.get('aliases') for r in stu['Example PI'].values())


def test_exact_joined_given_names_and_nicknames_remain_supported():
    assert same_student('Jun Yan Zhu', 'Junyan Zhu')
    assert same_student('Tom Lee', 'Thomas Lee')
    assert same_student('Ali Bagher', 'Alireza Bagher')
