"""Preserve real citation lists without selecting a primary owner from them."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import schema_check as S
import test_build_rules as T
from pihier import build, census, source_metadata

ROOT = Path(__file__).resolve().parents[1]
SOURCE = dict(url='http://www.cad.zju.edu.cn/home/liming/',
              sha256='fedea018c3d2961bfb9d173702ed73e74cb66b9a3850e103e0b3df8e2c88d327',
              quote='Our Team Ming Li Advisor', kind='owned_lab_single_advisor',
              observed='2026-11-08T02:56:28', observedAt='2026-11-08T02:56:28')


def schema():
    return json.loads((ROOT/'schemas/pis.schema.json').read_text())


def lab(evidence):
    source = dict(name='李明', lab_units=[dict(
        name='IDesign: Integrated & Intelligent Structure Design and Analysis',
        url=SOURCE['url'], evidence=evidence)])
    return census.choose_lab(source, {}, {}, [], ['李明', 'Ming Li'])


def test_actual_native_lab_citation_array_and_multiple_sources_are_preserved(tmp_path, monkeypatch, layout):
    import provenance
    T.write_school(tmp_path)
    ctx = T.run_stages(tmp_path)
    ctx.out = tmp_path/'package'; ctx.out.mkdir()
    monkeypatch.setattr(provenance, 'block', lambda school: {})
    build.write(ctx)
    pi = json.loads((ctx.out/'pis.json').read_text())[0]
    second = dict(url='https://example.edu/official-profile', sha256='b'*64,
                  quote='Independent official ownership citation')
    for evidence in [SOURCE, [SOURCE], [SOURCE, second], None]:
        before = copy.deepcopy(evidence)
        pi['lab'] = lab(evidence)
        assert pi['lab']['evidence'] == evidence
        assert S.validate([pi], schema()) == []
        assert evidence == before


@pytest.mark.parametrize('evidence', ['citation', 1, True, ['citation'], [None], [[SOURCE]], [SOURCE, 3]])
def test_scalar_and_mixed_citation_lists_fail_schema(evidence):
    shape = schema()['$defs']['pi']['properties']['lab']['properties']['evidence']
    assert S.validate(evidence, shape)


@pytest.mark.parametrize('evidence', [[SOURCE], [SOURCE, dict(SOURCE, quote='Another citation')]])
def test_primary_article_owner_binding_does_not_select_from_citation_array(evidence):
    ctx = SimpleNamespace(pid0={'李明': dict(lab=lab(evidence), names=['李明', 'Ming Li'])})
    claim = dict(authority=dict(homepage=dict(SOURCE, role_quote=SOURCE['quote'], name_quote='Ming Li'),
                                publication={}))
    before = copy.deepcopy((ctx.pid0, claim))
    assert source_metadata._primary_article_type(ctx, dict(pi='李明'), {}, claim) == 'primary_owner_binding_mismatch'
    assert (ctx.pid0, claim) == before
