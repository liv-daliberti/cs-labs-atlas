"""Lossless hot-path indices must agree with the original exhaustive rules, including large bylines."""
import copy
import itertools
import re

import pytest

from pihier import identity, papers
from pihier.names import Name, byline_name, nosuffix, toks


def exhaustive_advisee(names, others, pi_full):
    def full(raw):
        t = nosuffix(toks(byline_name(raw)))
        return len(t) >= 2 and len(t[0]) > 1
    return any(name.match(raw) and (pi_full or full(raw)) for name in names for raw in others)


NAMES = ['J. Andrew (Drew) Bagnell', 'Md Tauhidul Islam', 'S. Matthew Weinberg', 'Jun-Yan Zhu',
         'Maria Gonzalez Escamilla', 'Jean de La Fontaine', 'Arvind', '张荷花', 'Song GUO 郭嵩',
         'Ada Lovelace', 'William Smith', 'Xinyi Li']
BYLINES = NAMES + ['Drew Bagnell', 'Andrew Bagnell', 'M. T. Islam', 'Matthew Weinberg', 'Junyan Zhu',
                   'Maria Gonzalezescamilla', 'Jean Delafontaine', '郭嵩', 'Song Guo', 'A. Lovelace',
                   'Bill Smith', 'Xi Li', 'X. Li', '', 'A', 'Grace Hopper']


@pytest.mark.parametrize('pi_full', [False, True])
def test_candidate_index_agrees_with_exhaustive_name_and_full_guard_matrix(pi_full):
    for wanted, raw in itertools.product(NAMES, BYLINES):
        names = [Name([wanted])]
        assert identity._advisee_coauthor(names, [raw], pi_full) == exhaustive_advisee(names, [raw], pi_full)
    names = [Name([name]) for name in NAMES]
    assert identity._advisee_coauthor(names, BYLINES, pi_full) == exhaustive_advisee(names, BYLINES, pi_full)
    assert not identity._advisee_coauthor([], BYLINES, pi_full)


@pytest.mark.parametrize('pi_full', [False, True])
def test_5001_author_index_retains_last_actual_advisee_and_does_not_mutate(pi_full):
    bylines = [f'Person{index} Unrelated{index}' for index in range(5000)] + ['Ada Lovelace']
    before = list(bylines)
    names = [Name(['Grace Hopper']), Name(['Ada Lovelace'])]
    assert identity._advisee_coauthor(names, bylines, pi_full)
    assert identity._advisee_coauthor(names, bylines, pi_full) == exhaustive_advisee(names, bylines, pi_full)
    assert bylines == before
    assert not identity._advisee_coauthor(names[:1], bylines, pi_full)


@pytest.mark.parametrize('raw', ['Tsinghua University', 'Tsinghua University (Beijing)',
                                'Different Institute (Prof Other)'])
def test_unqualified_affiliations_do_not_normalize_any_coauthor(raw, monkeypatch):
    author = dict(raw_author_name='Ada Lovelace', raw_affiliation_strings=[raw])
    work = dict(authorships=[author] + [dict(raw_author_name=f'Person{i} Unrelated') for i in range(5000)])
    before = copy.deepcopy(work)
    def unexpected(_):
        raise AssertionError('No school author-owner qualifier exists; no coauthor normalization is necessary')
    monkeypatch.setattr(papers, '_affiliation_author_names', unexpected)
    assert not papers.school_affiliation_explicitly_other_author(work, author, re.compile('Tsinghua'))
    assert work == before


@pytest.mark.parametrize('raw,expected', [
    ('Tsinghua University (Dr Hopper)', True),
    ('Tsinghua University (Dr Lovelace)', False),
    ('Tsinghua University (Drs Hopper and Lovelace)', False),
    ('Tsinghua University (Dr Unknown)', False),
    ('Tsinghua University (Dr Hopper); Tsinghua University', False),
])
def test_qualified_school_owner_verdicts_remain_exact(raw, expected):
    target = dict(raw_author_name='Ada Lovelace', raw_affiliation_strings=[raw])
    work = dict(authorships=[target, dict(raw_author_name='Grace Hopper')])
    assert papers.school_affiliation_explicitly_other_author(work, target, re.compile('Tsinghua')) is expected
