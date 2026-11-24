"""Literal sourced Shenzhen campuses cannot borrow the broad parent ID."""
import copy
import re

import pytest

import school_config as S
import test_build_rules as B
from pihier import common as C, papers


# Keep spans bounded: an independent Beijing occurrence after this phrase
# must remain visible to the existing primary/dual-affiliation exception.
EXCLUDED = (r'\b(?:tsinghua|qinghua)\s+univ\w*\b\s*[,(-]\s*shenzhen\b|'
            r'\bgraduate\s+school\s+(?:of|at|in)\s+shenzhen\s*[,]\s*(?:tsinghua|qinghua)\s+univ\w*\b|'
            r'\btsinghua(?:[-\s]+berkeley)?\s+shenzhen\s+(?:international\s+graduate\s+school|institute)\b|'
            r'清华大学深圳(?:国际)?研究生院')
OBSERVED = ['Tsinghua University, Shenzhen, China',
            'Graduate School of Shenzhen, Tsinghua University']


@pytest.fixture
def campus_charter(monkeypatch):
    original = S.get
    cfg = original('tsinghua')
    configured = dict(cfg, affiliation=dict(cfg['affiliation'], excluded_regex=EXCLUDED))
    monkeypatch.setattr(S, 'get', lambda key: configured if key == 'tsinghua' else original(key))
    return configured


@pytest.mark.usefixtures('campus_charter')
@pytest.mark.parametrize('raw', OBSERVED + ['Graduate School of Shenzhen,\n  Tsinghua University'])
@pytest.mark.parametrize('metadata', ['primary_only', 'excluded_only', 'both', 'none'])
def test_literal_shenzhen_source_overrides_parent_institution_metadata(raw, metadata):
    parent = S.inst('tsinghua')
    excluded = B.OA + S.get('tsinghua')['ids']['openalex_excluded'][0]
    ids = {'primary_only': [parent], 'excluded_only': [excluded], 'both': [parent, excluded], 'none': []}[metadata]
    author = dict(raw_affiliation_strings=[raw], institutions=[dict(id=i, lineage=[parent, i]) for i in ids])
    before = copy.deepcopy(author)
    assert C.excluded_school_only(author, 'tsinghua')
    assert papers._authorship_school_via({}, author, parent, S.aff_rx('tsinghua'), school='tsinghua') == []
    assert author == before


@pytest.mark.usefixtures('campus_charter')
@pytest.mark.parametrize('raw', [
    ['Tsinghua University, Shenzhen, China', 'Department of Computer Science and Technology, Tsinghua University, Beijing, China'],
    ['Graduate School of Shenzhen, Tsinghua University; Department of Computer Science and Technology, Tsinghua University, Beijing, China'],
    ['Tsinghua University, Beijing, China; Graduate School of Shenzhen, Tsinghua University'],
    ['Graduate School of Shenzhen, Tsinghua University and Tsinghua University, Beijing, China'],
])
def test_independent_beijing_occurrence_survives_in_same_or_separate_raw_strings(raw):
    parent = S.inst('tsinghua')
    author = dict(raw_affiliation_strings=raw, institutions=[dict(id=parent, lineage=[parent])])
    before = copy.deepcopy(author)
    assert not C.excluded_school_only(author, 'tsinghua')
    assert papers._authorship_school_via({}, author, parent, S.aff_rx('tsinghua'), school='tsinghua')
    assert author == before


def test_configured_positive_school_regex_preserves_existing_charter_examples(campus_charter):
    positive = S.aff_rx('tsinghua')
    assert all(positive.search(text) for text in campus_charter['affiliation']['must_match'])
    assert all(not positive.search(text) for text in campus_charter['affiliation']['must_not_match'])
    negative = re.compile(EXCLUDED, re.I)
    assert all(negative.search(text) for text in OBSERVED)
    assert negative.search('Tsinghua Shenzhen International Graduate School')
    assert negative.search('Tsinghua-Berkeley Shenzhen Institute')
    assert negative.search('清华大学深圳国际研究生院')


@pytest.fixture
def native_campus_charter(monkeypatch):
    original = S.get
    source = original('tsinghua')
    def configured(key):
        cfg = original(key)
        if key != B.SCHOOL:
            return cfg
        # No excluded institution ID: the literal source must be sufficient.
        return dict(cfg, ids=dict(cfg['ids'], openalex_excluded=[], openalex_related=[]),
                    affiliation=dict(source['affiliation'], excluded_regex=EXCLUDED))
    monkeypatch.setattr(S, 'get', configured)


@pytest.mark.usefixtures('layout', 'native_campus_charter')
@pytest.mark.parametrize('raw', OBSERVED)
@pytest.mark.parametrize('dual', [False, True])
def test_native_paper_and_coauthor_flags_use_the_same_literal_campus_guard(tmp_path, raw, dual):
    affiliations = [raw] + (['Tsinghua University, Beijing, China'] if dual else [])
    author = B.au('Ada Lovelace', 'A1', raw=affiliations)
    work = B.work('WCAMPUS', 'A campus-bounded research paper', 2020, [author, B.au('Alan Turing', 'A9')])
    original = copy.deepcopy(work)
    B.write_school(tmp_path, sweep=[work])
    ctx = B.run_stages(tmp_path, upto='papers')
    rows = [r for r in ctx.rows if r['oa'] == work['id']]
    assert bool(rows) is dual
    if rows:
        assert 'Ada Lovelace' in rows[0]['byline_school']
    assert work == original
