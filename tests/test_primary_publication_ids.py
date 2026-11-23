"""New publisher source anchors retain normal DOI precedence and existing ID semantics."""
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
