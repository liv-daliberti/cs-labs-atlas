"""Mixed student/staff records retain the dates of each role when linking papers."""
from collections import Counter, defaultdict
from types import SimpleNamespace

import pytest

from pihier import links


def member():
    return dict(person='member', name='Dan Member', roles=['phd', 'staff'], relations=[
        dict(role='phd', years=[2017], sources=[]),
        dict(role='staff', years=[2026], sources=[]),
    ])


def test_later_staff_role_does_not_extend_student_window():
    assert links.near_relation(member(), 2018)
    assert not links.near_relation(member(), 2026)


@pytest.mark.parametrize('year,expected', [(2017, True), (2022, True), (2026, False)])
def test_unaffiliated_byline_uses_student_episode(tmp_path, year, expected):
    ctx = SimpleNamespace(school='example', here=tmp_path, n=Counter(), pls=defaultdict(list),
        stu={'Example PI': {'member': member()}},
        rows=[dict(pi='Example PI', work='work', oa='W1', year=year,
                   byline=['Example PI', 'Dan Member'],
                   _bylines=[(['Example PI', 'Dan Member'], [])])])
    links.link_students(ctx)
    assert bool(ctx.sp) is expected


@pytest.mark.parametrize('role', ['staff', 'research_scientist', 'research_engineer', 'postdoc', 'member'])
def test_nonstudent_members_do_not_gain_student_links(tmp_path, role):
    person = member()
    person.update(roles=[role], relations=[dict(role=role, years=[2026], sources=[])])
    ctx = SimpleNamespace(school='example', here=tmp_path, n=Counter(), pls=defaultdict(list),
        stu={'Example PI': {'member': person}},
        rows=[dict(pi='Example PI', work='work', oa='W1', year=2026,
                   byline=['Example PI', 'Dan Member'],
                   _bylines=[(['Example PI', 'Dan Member'], ['Dan Member'])])])
    links.link_students(ctx)
    assert ctx.sp == []


def test_legacy_unlabelled_relations_keep_their_window():
    person = member()
    person['relations'] = [dict(years=[2017])]
    assert links.near_relation(person, 2018)
    assert not links.near_relation(person, 2026)
