"""New publisher source anchors retain normal DOI precedence and existing ID semantics."""
import csv
import gzip
import json
from pathlib import Path

import pytest

import atlas_ids as A
import atlas_paths as P
import schema_check as S


def test_genuine_publisher_anchors_are_separate_from_provider_and_labpage_ids():
    publisher = 'publisher:' + 'a' * 40
    assert A.work_anchors(dict(oa=publisher), 'whu') == {('publisher', 'a' * 40)}
    assert A.work_anchors(dict(oa=publisher, doi='10.16512/j.cnki.jsjjy.2017.08.019'), 'whu') == {
        ('publisher', 'a' * 40), ('doi', '10.16512/j.cnki.jsjjy.2017.08.019')}
    assert A.RANK['doi'] < A.RANK['publisher']
    assert A.WSCHEME['publisher'] == 'publisher'
    assert A.work_anchors(dict(oa='labpage:' + 'a' * 40), 'whu') == {('labpage', 'a' * 40)}
    assert not A.work_anchors(dict(oa='publisher:not-a-real-key'), 'whu')


def test_publication_schema_accepts_new_source_without_accepting_fake_provider_id():
    schema = json.loads((Path(__file__).parents[1] / 'schemas/lab_papers.schema.json').read_text())
    assert not S.validate('publisher:' + 'a' * 40, schema['properties']['oa'])
    assert S.validate('https://openalex.org/publisher/123', schema['properties']['oa'])
    assert not S.validate('reviewed_primary_publisher', schema['properties']['identity'])


@pytest.mark.parametrize('layout', ['flat', 'split'])
def test_native_publisher_records_allocate_and_export_stable_work_ids(tmp_path, monkeypatch, layout):
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', layout)
    from test_atlas_ids import paper, pi, write

    root = tmp_path / 'trial'
    article_key = 'publisher:42b19a9fb6b25123620510a18551ba10ed8ba693'
    book_key = 'publisher:0a7cf859b81f5a29376917c005dd950b01af4bc3'
    doi = '10.16512/j.cnki.jsjjy.2017.08.019'
    write(root, dict(whu=dict(
        pis=[pi('贺莲', personIds=['whu_he_lian']), pi('李春葆', personIds=['whu_li_chunbao'])],
        students={}, links=[], sweep=[], papers=[
            paper('贺莲', article_key, doi=doi, title='以计算思维能力为导向的硬件课程体系建设'),
            paper('李春葆', book_key, title='数据结构教程（第6版）学习指导')])))
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    A.run(['whu'], root, db, use_sweep=False, published={}, today='2026-11-23')
    with gzip.open(P.hfile(root, 'lab_papers.jsonl.gz', 'whu'), 'rt') as stream:
        rows = {r['pi']: r for r in map(json.loads, stream)}
    with gzip.open(P.hfile(root, 'ids') / 'crossref.tsv.gz', 'rt') as stream:
        refs = list(csv.DictReader(stream, delimiter='\t'))
    for name, key in [('贺莲', article_key), ('李春葆', book_key)]:
        wid = rows[name]['atlasWorkId']
        assert wid.startswith('atl:w:')
        assert dict(atlas_id=wid, entity='work', scheme='publisher', value=key[10:]) in refs
        assert not any(r['atlas_id'] == wid and r['scheme'] in {'openalex_work', 'labpage'} for r in refs)
    assert dict(atlas_id=rows['贺莲']['atlasWorkId'], entity='work', scheme='doi', value=doi) in refs
    before = {t: sorted(db.execute('select * from ' + t).fetchall()) for t in ['ids', 'anchors']}
    exported = (P.hfile(root, 'ids') / 'crossref.tsv.gz').read_bytes()
    A.run(['whu'], root, db, use_sweep=False, published={}, today='2026-11-23')
    assert before == {t: sorted(db.execute('select * from ' + t).fetchall()) for t in before}
    assert (P.hfile(root, 'ids') / 'crossref.tsv.gz').read_bytes() == exported
    db.close()


def test_complete_native_publisher_rows_pass_the_export_schema():
    # Exact native rows from the WHU 2017 article / 2022 book candidate. Validate
    # the complete export contract, including source and appointment fields.
    schema = json.loads((Path(__file__).parents[1] / 'schemas/lab_papers.schema.json').read_text())
    rows = [{'pi': '贺莲',
  'work': None,
  'oa': 'publisher:42b19a9fb6b25123620510a18551ba10ed8ba693',
  'doi': '10.16512/j.cnki.jsjjy.2017.08.019',
  'title': '以计算思维能力为导向的硬件课程体系建设',
  'year': 2017,
  'date': '2017-08-10',
  'type': 'article',
  'venue': '计算机教育',
  'landing': 'https://jyjs.cbpt.cnki.net/portal/journal/portal/client/paper/a9e2afa02860540f8f93eed942036c8e',
  'byline': ['贺莲', '龚奕利', '蔡朝晖', '刘树波'],
  'byline_school': [],
  'authorship': {'position': None,
                 'raw_name': None,
                 'author_id': None,
                 'institutions': [],
                 'raw_affiliations': [],
                 'school_via': ['primary publisher '
                                '[9e12723d6dd58f1b086bbeb097ef8eb96f37c9cc839fe488754fa1937b9aac77] '
                                'https://jyjs.cbpt.cnki.net/portal/journal/portal/client/paper/a9e2afa02860540f8f93eed942036c8e: '
                                '贺莲 龚奕利 蔡朝晖 刘树波 1.武汉大学计算机学院'],
                 'page1': None},
  'identity': 'reviewed_primary_publisher',
  'appointment': {'listing': {'url': 'https://web.archive.org/web/20170414114250id_/http://cs.whu.edu.cn:80/plus/list.php?tid=36',
                              'sha256': 'e2d1d74728162d9795236a1ac0ae45e26b61ab5877e17e9d831fc797e80eed09',
                              'quote': '贺莲副教授',
                              'kind': 'dept_listing:CS',
                              'year': 2017}},
  'source': 'publisher_recover:reviewed_primary_publisher',
  'editions': []},
 {'pi': '李春葆',
  'work': None,
  'oa': 'publisher:0a7cf859b81f5a29376917c005dd950b01af4bc3',
  'doi': None,
  'title': '数据结构教程（第6版）学习指导',
  'year': 2022,
  'date': '2022',
  'type': 'book',
  'venue': '清华大学出版社',
  'landing': 'https://www.tup.tsinghua.edu.cn/booksCenter/book_09395601.html',
  'byline': ['李春葆', '尹为民', '蒋晶珏', '喻丹丹', '蒋林'],
  'byline_school': [],
  'authorship': {'position': None,
                 'raw_name': None,
                 'author_id': None,
                 'institutions': [],
                 'raw_affiliations': [],
                 'school_via': ['primary publisher '
                                '[696951fc6c79bb324493d870b1e45cec036afa345ce83a7bb10b520e613225a6] '
                                'https://www.tup.tsinghua.edu.cn/booksCenter/book_09395601.html: '
                                '李春葆，武汉大学计算机学院，职务：无，职称：教授'],
                 'page1': None},
  'identity': 'reviewed_primary_publisher',
  'appointment': {'listing': {'url': 'https://web.archive.org/web/20221103122653id_/http://cs.whu.edu.cn/szdw/zrjs.htm',
                              'sha256': '58ddf37b8676cb9e04f0756c51646c217dd462278f36f58efc8763e613dcf506',
                              'quote': '李春葆 男 教授 (硕导)',
                              'kind': 'dept_listing:CS',
                              'year': 2022}},
  'source': 'publisher_recover:reviewed_primary_publisher',
  'editions': []}]
    for row in rows:
        assert not S.validate(row, schema)
        assert S.validate(dict(row, source='publisher_recover:unreviewed'), schema)
