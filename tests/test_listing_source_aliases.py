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


@pytest.mark.parametrize('alias,quote', [
    ('陈彦', '姓名：陈彦 职称：教授 学院：网络空间安全学院'),
    ('张文逸', '张文逸博士担任电子工程与信息科学系教授。'),
    ('周 颢', '周 颢 副教授 通信网络'),
])
def test_recorded_literal_chinese_full_alias_proves_actual_year(alias, quote):
    row = person(quote)
    row['name'] = 'Existing English Identity'
    row['aliases'] = [alias]
    assert set(listings(row)) == {2026}
    row['sources'][0]['observed'] = '20211117'
    assert set(listings(row)) == {2021}


@pytest.mark.parametrize('alias,quote', [
    ('陈', '陈彦 教授'),
    ('陈彦', '陈 张 彦 教授'),
    ('张文逸', '张文 教授'),
    ('Yan Chen', '陈彦 教授'),
])
def test_literal_alias_requires_recorded_complete_name(alias, quote):
    row = person(quote)
    row['name'] = 'Existing English Identity'
    row['aliases'] = [alias]
    assert listings(row) == {}


def test_literal_alias_keeps_source_and_faculty_guards():
    row = person('陈彦 PhD student')
    row['name'] = 'Existing English Identity'
    row['aliases'] = ['陈彦']
    assert listings(row) == {}
    row['sources'][0]['quote'] = '陈彦 教授'
    row['sources'][0]['sha256'] = ''
    assert listings(row) == {}
