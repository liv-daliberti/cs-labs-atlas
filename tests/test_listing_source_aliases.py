"""Full recorded aliases can bind a faculty observation without creating a career interval."""
import collections
import copy

import pytest

from pihier.periods import pi_listings


def person(quote='Yongcheng Jing is a Full Professor at Wuhan University.'):
    return dict(name='静永程', aliases=['Yongcheng Jing'], years_listed=[2026], sources=[dict(
        url='https://faculty.example/profile', sha256='a' * 64,
        observed='20261118', quote=quote, kind='owned_faculty_profile')])


def listings(row):
    return pi_listings(row, {}, collections.Counter())


def test_full_recorded_alias_proves_only_the_actual_source_year():
    row = person()
    before = copy.deepcopy(row)
    result = listings(row)
    assert set(result) == {2026}
    assert result[2026]['quote'] == row['sources'][0]['quote']
    assert set(result[2026]) == {'url', 'sha256', 'quote', 'kind', 'year'}
    assert row == before


@pytest.mark.parametrize('quote', [
    'Jing is a Professor at Wuhan University.',
    'Y. Jing is a Professor at Wuhan University.',
    'Yongcheng J. is a Professor at Wuhan University.',
    'Yongcheng Jingxiao is a Professor at Wuhan University.',
    'Another Yongcheng and another Jing are faculty.',
])
def test_partial_initial_and_noncontiguous_aliases_do_not_bind(quote):
    assert listings(person(quote)) == {}


@pytest.mark.parametrize('alias', ['Jing', 'Y. Jing', 'Yongcheng J.', 'Yongcheng C. Jing'])
def test_an_initial_or_surname_alias_is_not_full_name_authority(alias):
    row = person(alias + ' is a Professor at Wuhan University.')
    row['aliases'] = [alias]
    assert listings(row) == {}


@pytest.mark.parametrize('quote', [
    'Yongcheng Jing is a postdoctoral researcher at Wuhan University.',
    'Yongcheng Jing is a PhD student at Wuhan University.',
    'Yongcheng Jing will join Wuhan University as a Professor.',
])
def test_full_alias_does_not_waive_faculty_and_future_role_guards(quote):
    assert listings(person(quote)) == {}


@pytest.mark.parametrize('field,value', [('sha256', ''), ('observed', ''), ('observed', '20150101')])
def test_full_alias_cannot_supply_a_hash_date_or_window(field, value):
    row = person()
    row['sources'][0][field] = value
    assert listings(row) == {}


def test_absent_alias_is_not_generated_from_a_chinese_name():
    row = person()
    row['aliases'] = []
    assert listings(row) == {}
