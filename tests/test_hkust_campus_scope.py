"""Observed Guangzhou variants cannot borrow a derived Hong Kong institution ID."""
import copy
import pytest
import school_config as S
from pihier import common as C

PRIMARY='https://openalex.org/I200769079'
EXCLUDED='https://openalex.org/I4405261251'

@pytest.mark.parametrize('raw',[
    'The Hong Kong University of Science and Technology (Guangzhou )',
    'HKUST(GZ )', 'HKUST ( GZ )', 'HKUST (Guang Zhou)',
])
def test_spacing_does_not_turn_an_explicit_guangzhou_university_into_hong_kong(raw):
    assert not S.aff_rx('hkust').search(raw)


def authorship(raw,primary=True):
    entries=[dict(id=EXCLUDED,lineage=[EXCLUDED])]
    if primary:entries.append(dict(id=PRIMARY,lineage=[PRIMARY]))
    return dict(institutions=entries,raw_affiliation_strings=raw)


@pytest.mark.parametrize('raw',[
    ['HKUST (GZ)'],['HKUST(GZ )'],
    ['The Hong Kong University of Science and Technology (Guangzhou )'],
])
def test_explicit_excluded_variant_holds_even_when_metadata_adds_the_primary_id(raw):
    a=authorship(raw);before=copy.deepcopy(a)
    assert C.excluded_school_only(a,'hkust')
    assert a==before


@pytest.mark.parametrize('raw',[
    ['HKUST (GZ) and HKUST'],
    ['HKUST(GZ )','Department of Computer Science and Engineering, HKUST, Hong Kong'],
    ['Hong Kong University of Science and Technology (Guangzhou), China and Hong Kong University of Science and Technology, Hong Kong'],
])
def test_independent_primary_or_dual_raw_affiliation_still_supports_hong_kong(raw):
    assert not C.excluded_school_only(authorship(raw),'hkust')


def test_missing_raw_text_is_not_invented_as_an_explicit_campus_contradiction():
    assert not C.excluded_school_only(authorship([]),'hkust')
    assert C.excluded_school_only(authorship([],primary=False),'hkust')


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('dual',[False,True])
def test_native_pi_identity_and_school_coauthor_do_not_override_explicit_branch_only_raw(tmp_path,monkeypatch,dual):
    import test_build_rules as B
    original=S.get
    def config(key):
        cfg=original(key)
        if key!='princeton':return cfg
        hk=original('hkust')
        return dict(cfg,ids=dict(cfg['ids'],openalex_excluded=['I999999']),affiliation=hk['affiliation'])
    monkeypatch.setattr(S,'get',config)
    monkeypatch.setitem(C.SCHOOL_LOOSE,'princeton',original('hkust')['affiliation']['loose'])
    own=B.au('Ada Lovelace','A1');own['institutions'].append(dict(id=B.OA+'I999999',lineage=[B.OA+'I999999']))
    own['raw_affiliation_strings']=['HKUST (GZ) and HKUST' if dual else 'HKUST(GZ )']
    paper=B.work('WCAMPUS','A Source Bound Campus Paper',2020,[own,B.au('Alan Turing','A9')])
    B.write_school(tmp_path,sweep=[paper]);ctx=B.run_stages(tmp_path,upto='papers')
    assert any(r['oa']==paper['id'] for r in ctx.rows) is dual
