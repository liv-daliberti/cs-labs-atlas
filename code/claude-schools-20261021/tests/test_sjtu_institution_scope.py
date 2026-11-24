"""XJTLU-only evidence cannot borrow SJTU metadata; real SJTU evidence survives."""
import copy

import pytest
import school_config as S
from pihier import common as C, papers

PRIMARY = 'https://openalex.org/I183067930'
XJTLU = 'https://openalex.org/I69356397'


def institution(identifier, lineage=None):
    return dict(id=identifier, display_name='Synthetic institution metadata',
                lineage=lineage if lineage is not None else [identifier])


def authorship(raw, institutions):
    return dict(raw_author_name='Synthetic PI',
                author=dict(id='synthetic:own', display_name='Synthetic PI'),
                raw_affiliation_strings=raw, institutions=institutions)


def school_via(own):
    coauthor = authorship(['上海交通大学'], [institution(PRIMARY)])
    coauthor['author'] = dict(id='synthetic:other', display_name='Other author')
    coauthor['raw_author_name'] = 'Other author'
    work = dict(id='synthetic:scope-paper', authorships=[own, coauthor])
    before = copy.deepcopy(work)
    scoped = C.gate_related(work, C.related_gate('sjtu'))
    via = papers._authorship_school_via(
        scoped, scoped['authorships'][0], PRIMARY, S.aff_rx('sjtu'), school='sjtu')
    assert work == before
    return via


@pytest.mark.parametrize('raw', [
    "Xi'an Jiaotong-Liverpool University", 'Xi’an Jiaotong-Liverpool University',
    '西交利物浦大学', 'XJTLU',
])
@pytest.mark.parametrize('extra_excluded_entry', [False, True])
def test_xjtlu_only_raw_cannot_borrow_misassigned_primary_or_school_coauthor(raw, extra_excluded_entry):
    entries = [institution(PRIMARY)]
    if extra_excluded_entry:
        entries.append(institution(XJTLU, [XJTLU, PRIMARY]))
    own = authorship([raw], entries)
    before = copy.deepcopy(own)
    assert C.excluded_school_only(own, 'sjtu')
    assert school_via(own) == []
    assert own == before


def test_xjtlu_inherited_primary_is_removed_on_copy_without_inventing_raw_text():
    own = authorship([], [institution(XJTLU, [XJTLU, PRIMARY])])
    assert school_via(own) == []
    assert own['institutions'][0]['lineage'] == [XJTLU, PRIMARY]
    assert own['raw_affiliation_strings'] == []


@pytest.mark.parametrize('raw', [
    ['西交利物浦大学与上海交通大学'],
    ["Xi'an Jiaotong-Liverpool University and Shanghai Jiao Tong University"],
    ['西交利物浦大学', '上海交通大学'],
])
def test_independent_explicit_sjtu_dual_raw_survives(raw):
    own = authorship(raw, [institution(XJTLU, [XJTLU, PRIMARY])])
    assert not C.excluded_school_only(own, 'sjtu')
    assert school_via(own)


def test_separate_primary_entry_survives_without_excluded_only_raw_contradiction():
    own = authorship([], [institution(XJTLU, [XJTLU, PRIMARY]), institution(PRIMARY)])
    assert school_via(own)


@pytest.mark.parametrize('campus', ['徐汇', '闵行', '黄浦', '长宁', '浦东', '崇明'])
def test_six_proper_sjtu_campuses_remain_primary(campus):
    assert school_via(authorship(['上海交通大学' + campus + '校区'], [institution(PRIMARY)]))


@pytest.mark.parametrize('place', ['苏州', '太仓'])
def test_geography_alone_is_not_an_xjtlu_exclusion(place):
    assert school_via(authorship([place], [institution(PRIMARY)]))


def test_existing_xian_guard_remains_and_other_child_policy_is_unchanged():
    assert school_via(authorship(['西安交通大学'], [institution(PRIMARY)])) == []
    # An unresolved child's synthetic inherited-primary hazard is separate from XJTLU.
    child = 'https://openalex.org/I4210140493'
    assert school_via(authorship(
        ['Collaborative Innovation Center of Advanced Microstructures'],
        [institution(child, [child, PRIMARY])]))


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('dual', [False, True])
def test_native_paper_stage_holds_xjtlu_only_pi_but_preserves_true_primary_dual(tmp_path, monkeypatch, dual):
    import test_build_rules as B

    original = S.get
    sjtu = original('sjtu')

    def config(key):
        cfg = original(key)
        if key != 'princeton':
            return cfg
        # Reuse the isolated PI fixture with the actual SJTU affiliation policy.
        return dict(cfg, affiliation=sjtu['affiliation'],
                    ids=dict(cfg['ids'], openalex_related=[],
                             openalex_excluded=sjtu['ids']['openalex_excluded']))

    monkeypatch.setattr(S, 'get', config)
    monkeypatch.setitem(C.SCHOOL_LOOSE, 'princeton', sjtu['affiliation']['loose'])
    raw = ['西交利物浦大学'] + (['上海交通大学'] if dual else [])
    own = B.au('Ada Lovelace', 'A1', raw=raw)
    paper = B.work('WXJTLUSCOPE', 'A Source Bound Institutional Scope Paper', 2020,
                   [own, B.au('Alan Turing', 'A9')])
    before = copy.deepcopy(paper)
    B.write_school(tmp_path, sweep=[paper])
    ctx = B.run_stages(tmp_path, upto='papers')
    assert any(row['oa'] == paper['id'] for row in ctx.rows) is dual
    assert paper == before
