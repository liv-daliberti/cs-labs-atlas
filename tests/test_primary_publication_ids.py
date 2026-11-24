"""New publisher source anchors retain normal DOI precedence and existing ID semantics."""
import csv
import gzip
import json
from pathlib import Path

import atlas_ids as A
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


def test_native_publisher_records_allocate_and_export_stable_work_ids(tmp_path):
    from test_atlas_ids import paper, pi, write

    root = tmp_path / 'hierarchy'
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
    with gzip.open(root / 'whu/lab_papers.jsonl.gz', 'rt') as stream:
        rows = {r['pi']: r for r in map(json.loads, stream)}
    with gzip.open(root / 'ids/crossref.tsv.gz', 'rt') as stream:
        refs = list(csv.DictReader(stream, delimiter='\t'))
    for name, key in [('贺莲', article_key), ('李春葆', book_key)]:
        wid = rows[name]['atlasWorkId']
        assert wid.startswith('atl:w:')
        assert dict(atlas_id=wid, entity='work', scheme='publisher', value=key[10:]) in refs
        assert not any(r['atlas_id'] == wid and r['scheme'] in {'openalex_work', 'labpage'} for r in refs)
    assert dict(atlas_id=rows['贺莲']['atlasWorkId'], entity='work', scheme='doi', value=doi) in refs
    before = {t: sorted(db.execute('select * from ' + t).fetchall()) for t in ['ids', 'anchors']}
    exported = (root / 'ids/crossref.tsv.gz').read_bytes()
    A.run(['whu'], root, db, use_sweep=False, published={}, today='2026-11-23')
    assert before == {t: sorted(db.execute('select * from ' + t).fetchall()) for t in before}
    assert (root / 'ids/crossref.tsv.gz').read_bytes() == exported
    db.close()
