"""Literal excluded-campus names outrank derived IDs; independent own evidence survives."""
import collections
import copy
import re
from types import SimpleNamespace

import pytest
import school_config as S
from pihier import common as C, papers
import test_build_rules as B


OBSERVED = [
    'Hong Kong University of Science and Technology Guangzhou Information Hub',
    'HKUST(GZ) / HKUST Guangzhou / Hong Kong , China',
    'DSA , HKUST (GZ)&HKUST Guangzhou , China',
    'Hong Kong University of Science and Technology , Guangzhou , China',
]


@pytest.mark.parametrize('raw', OBSERVED)
@pytest.mark.parametrize('metadata', ['primary_only', 'excluded_only', 'both', 'none'])
def test_original_literal_variants_cannot_borrow_primary_metadata(raw, metadata):
    ids = {'primary_only': ['I200769079'], 'excluded_only': ['I4405261251'],
           'both': ['I200769079', 'I4405261251'], 'none': []}[metadata]
    a = dict(institutions=[dict(id=B.OA + i, lineage=[B.OA + i]) for i in ids],
             raw_affiliation_strings=[raw])
    before = copy.deepcopy(a)
    assert not S.aff_rx('hkust').search(raw)
    assert C.excluded_school_only(a, 'hkust')
    assert papers._authorship_school_via({}, a, B.OA + 'I200769079', S.aff_rx('hkust'), school='hkust') == []
    assert a == before


@pytest.mark.parametrize('raw', [
    ['HKUST Guangzhou and HKUST, Hong Kong'],
    ['HKUST(GZ)', 'HKUST, Hong Kong SAR, China'],
    ['Hong Kong University of Science and Technology Guangzhou Information Hub',
     'Department of Computer Science and Engineering, Hong Kong University of Science and Technology, Hong Kong'],
])
def test_independent_primary_or_dual_raw_remains_available(raw):
    assert not C.excluded_school_only(dict(institutions=[], raw_affiliation_strings=raw), 'hkust')


@pytest.fixture
def configured(monkeypatch):
    original = S.get
    def config(key):
        cfg = original(key)
        if key != 'princeton':
            return cfg
        # Deliberately no excluded IDs: this catches a falsely derived primary-only institution mapping.
        return dict(cfg, ids=dict(cfg['ids'], openalex_excluded=[], openalex_related=[]),
                    affiliation=original('hkust')['affiliation'])
    monkeypatch.setattr(S, 'get', config)
    monkeypatch.setitem(C.SCHOOL_LOOSE, 'princeton', original('hkust')['affiliation']['loose'])


@pytest.mark.usefixtures('layout', 'configured')
@pytest.mark.parametrize('dual', [False, True])
def test_native_pi_and_coauthor_routes_respect_explicit_text_without_excluded_IDs(tmp_path, dual):
    own = B.au('Ada Lovelace', 'A1', raw=[OBSERVED[-1]] + (['HKUST, Hong Kong'] if dual else []))
    paper = B.work('WEXPLICITCAMPUS', 'A Native Campus Scope Study', 2020, [own, B.au('Alan Turing', 'A9')])
    original = copy.deepcopy(paper)
    B.write_school(tmp_path, sweep=[paper])
    ctx = B.run_stages(tmp_path, upto='papers')
    assert any(row['oa'] == paper['id'] for row in ctx.rows) is dual
    assert paper == original


@pytest.mark.usefixtures('configured')
def test_independent_primary_page_can_rescue_misassigned_raw_metadata():
    own = B.au('Ada Lovelace', 'A1', raw=[OBSERVED[-1]])
    w = B.work('WPAGECAMPUS', 'A Primary Campus Proof', 2020, [own, B.au('Alan Turing', 'A9')])
    proof = dict(how='named byline', quotes=['Ada Lovelace, Princeton University'])
    ctx = SimpleNamespace(school='princeton', n=collections.Counter(), inst=B.INST,
                          aff=re.compile('Princeton University', re.I), tied={w['id']: proof},
                          pi_units=collections.defaultdict(set), school_units=set(),
                          anchored=collections.defaultdict(collections.Counter),
                          advisee_names=collections.defaultdict(list), adv_full=collections.defaultdict(set),
                          from_pw=set(), pid0={'Ada Lovelace': {'names': ['Ada Lovelace']}})
    via, page = papers.school_basis(ctx, 'Ada Lovelace', w, own, 'reviewed_openalex_author_id', None)
    assert via and via[0].startswith('page 1') and page == proof
    ctx.tied = {}
    assert papers.school_basis(ctx, 'Ada Lovelace', w, own, 'reviewed_openalex_author_id', None)[0] == []


def test_exclusion_pattern_is_validated(monkeypatch):
    original = S.get
    monkeypatch.setattr(S, 'get', lambda k: dict(original(k), affiliation=dict(original(k)['affiliation'], excluded_regex='[')))
    assert any('affiliation.excluded_regex does not compile' in issue for issue in S.check('hkust'))
