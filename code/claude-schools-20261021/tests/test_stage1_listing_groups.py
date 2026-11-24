import json

import pytest

from tools import stage_gate as G


@pytest.fixture
def listing_group(tmp_path, monkeypatch):
    group = dict(name='All categories', slots=['Faculty', 'Faculty lecturers'], **{'from': '20240101', 'to': '20261231'})
    department = dict(code='CS', listings=[dict(slot=s) for s in group['slots']], listing_groups=[group])
    config = dict(window=[2023, 2024], departments=[department])
    monkeypatch.setattr(G.S, 'get', lambda key: config)
    monkeypatch.setattr(G.P, 'data', lambda name, key: tmp_path / name)
    coverage = {'CS': {'2023': {'Earlier whole directory H1': 'ok'},
                       '2024': {'Faculty H1': 'ok', 'Faculty lecturers H2': 'ok'}}}

    def evaluate():
        (tmp_path / 'coverage.json').write_text(json.dumps(coverage))
        return G.g1_years('u')

    evaluate.bad = lambda: G.g1('u')[0]
    return config, department, coverage, evaluate


def test_group_requires_each_category_and_preserves_earlier_whole_directory(listing_group):
    _, _, coverage, evaluate = listing_group
    assert evaluate() == []
    coverage['CS']['2024'].pop('Faculty lecturers H2')
    assert evaluate() == ['CS 2024: All categories missing Faculty lecturers']
    coverage['CS']['2024']['Unrelated complete source H1'] = 'ok'
    assert evaluate() == ['CS 2024: All categories missing Faculty lecturers']


def test_partial_category_and_similar_slot_prefix_do_not_count(listing_group):
    _, _, coverage, evaluate = listing_group
    coverage['CS']['2024']['Faculty lecturers H2'] = 'unusable: missing page'
    assert 'Faculty lecturers' in evaluate()[0]
    coverage['CS']['2024'] = {'Faculty lecturers H2': 'ok'}
    assert evaluate() == ['CS 2024: All categories missing Faculty']


def test_complete_live_category_can_fill_its_actual_year(listing_group):
    _, _, coverage, evaluate = listing_group
    coverage['CS']['2024'] = {'Faculty H1': 'ok', 'Faculty lecturers live H2': 'ok'}
    assert evaluate() == []


@pytest.mark.parametrize('change', [dict(slots=[]), dict(slots=['Unknown']), dict(slots=['Faculty', 'Faculty']),
                                   {'from': '20250101', 'to': '20240101'}, {'from': '2024'}])
def test_invalid_group_fails_closed(listing_group, change):
    _, department, _, evaluate = listing_group
    department['listing_groups'][0].update(change)
    evaluate()
    assert evaluate.bad() == ["CS: invalid listing group 'All categories'"]
