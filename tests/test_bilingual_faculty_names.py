"""A bilingual faculty label must retain its explicitly written Latin-name reading."""
import copy
import gzip
import json

import pytest

import test_build_rules as T
from pihier import identity
from pihier.names import Name, full_pair, names_full_form


@pytest.mark.parametrize('display,byline', [
    ('Xiaofang ZHOU 周曉方', 'Xiaofang Zhou'),
    ('Raymond Chi-Wing WONG 黃智榮', 'Raymond Chi-Wing Wong'),
    ('李默 Mo LI', 'Mo Li'),
    ('Bo LI李波', 'Bo Li'),
])
def test_explicit_latin_reading_of_bilingual_label(display, byline):
    assert Name([display]).match(byline)
    assert Name([byline]).match(display)
    assert full_pair(display) == full_pair(byline)
    assert names_full_form('Adviser: ' + byline, [display])


def test_literal_chinese_names_stay_exact_without_invented_romanizations():
    assert Name(['孙家广']).match('孙家广')
    assert not Name(['孙家广']).match('Jiaguang Sun')
    assert not Name(['Xiaofang ZHOU 周曉方']).match('Xiaofang Chen')


@pytest.mark.usefixtures('layout')
def test_bilingual_census_pi_keeps_native_latin_byline_papers(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)
    title = 'A Native Research Paper With A Bilingual Faculty Label'
    doi = '10.9/bilingual-native'
    paper = T.work('W501', title, 2020, [T.au('Ada Lovelace', 'A1')], doi=doi)
    T.write_school(tmp_path, sweep=[paper])
    display = 'Ada Lovelace 艾达'
    path = T.put(tmp_path, 'census-faculty.json')
    census = json.loads(path.read_text())
    census[0]['name'] = display
    path.write_text(json.dumps(census))
    path = T.put(tmp_path, 'collection.json.gz')
    collection = json.loads(gzip.decompress(path.read_bytes()))
    collection['people'][0]['name'] = display  # no separate plain-name collection alias can mask this failure
    path.write_bytes(gzip.compress(json.dumps(collection).encode()))
    overrides = copy.deepcopy(T.OVERRIDES)
    overrides[T.SCHOOL][display] = overrides[T.SCHOOL].pop('Ada Lovelace')
    pid = 'https://dblp.org/pid/example/AdaLovelace'
    overrides[T.SCHOOL][display].update(openalex=[], mixed_openalex=[], dblp=[pid])
    T.put(tmp_path, 'census-overrides.json', None).write_text(json.dumps(overrides))
    own = dict(persons={pid: dict(names=['Ada Lovelace'], pubs=[dict(
        key='journals/example/Lovelace20', title=title, year=2020, dois=[doi], authors=['Ada Lovelace'])])}, by_name={})
    T.put(tmp_path, 'dblp-dump-persons-school.json.gz').write_bytes(gzip.compress(json.dumps(own).encode()))
    ctx = T.run_stages(tmp_path, upto='papers')
    assert ctx.pid0[display]['names'] == [display]
    assert title in T.rows_of(ctx, display)
    assert ctx.nm[display].match('Ada Lovelace')
