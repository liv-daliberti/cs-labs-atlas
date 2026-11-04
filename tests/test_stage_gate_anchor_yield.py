"""ROADMAP #43: an identity anchor must yield papers. A DBLP pid that gives no titles and no OpenAlex id passed stage 5 for ten
Georgia Tech PIs with 0 papers; the gate and the release preflight now fail such a PI unless a reason is recorded."""
import json

import pytest

import atlas_paths as P
import atlas_release as AR
import stage_gate as G


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    (tmp_path / 'u').mkdir()
    (tmp_path / '_').mkdir()

    def put(name, obj, key='u'):
        (tmp_path / key / name).write_text(json.dumps(obj))
    put('census-faculty.json', {'faculty': [dict(name='Ann', is_pi=True, dblp=['https://dblp.org/pid/a/Ann']),
                                            dict(name='Bo', is_pi=True, dblp=['https://dblp.org/pid/b/Bo'])]})
    return put


def pis(*counts):
    return [dict(pi=n, dblp=['d'], orcid=[], reviewedOpenAlex=[], counts=dict(verifiedWorks=v, labPapers=lp)) for n, v, lp in counts]


def test_anchor_without_papers_fails_the_gate(tree):
    tree('pis.json', pis(('Ann', 3, 5), ('Bo', 0, 0)))
    bad, counts = G.g5('u')
    assert len(bad) == 1 and bad[0].startswith('Bo: anchors yield 0 papers') and 'DBLP' in bad[0]
    assert G.evaluate('u', 5)['gate'] == 'fail' and counts['anchors_yield_checked'] is True


def test_recorded_reasons_pass(tree):
    tree('pis.json', pis(('Ann', 0, 0), ('Bo', 0, 0)))
    tree('census-overrides-school.json', {'Ann': {'no_papers': True, 'why_no_papers': 'searched DBLP, ORCID and homepage: no papers in the window'}})
    tree('lab-coverage-reasons.json', {'Bo': {'papers': {'code': 'sources_exhausted', 'why': 'emeritus, nothing published since 2016'}}})
    assert G.g5('u')[0] == []
    tree('census-overrides-school.json', {'Ann': {'no_papers': True}})   # a flag without its why is no reason
    assert [b.split(':')[0] for b in G.g5('u')[0]] == ['Ann']


def test_no_package_yet_is_not_measured(tree):
    bad, counts = G.g5('u')
    assert bad == [] and counts['anchors_yield_checked'] is False


def test_release_preflight_lists_the_flagged_pis(tree):
    tree('pis.json', pis(('Ann', 1, 1), ('Bo', 0, 0)))
    msg = AR.anchor_yield_problems(['u'])
    assert msg.startswith('anchors:') and 'u 1 (Bo)' in msg
    tree('pis.json', pis(('Ann', 1, 1), ('Bo', 2, 0)))
    assert AR.anchor_yield_problems(['u']) == ''
