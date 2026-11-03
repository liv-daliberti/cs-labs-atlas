"""R-PAP-28 (period boundaries and continuity bridges: Klasnja at Michigan) and R-PAP-29 (cross-affiliated bylines: Wenisch's
HPCA 2016 paper), 2026-11-02, on the synthetic school of test_build_rules."""
import copy

import pytest

import test_build_rules as T
from pihier import periods

OA, au, work = T.OA, T.au, T.work
pytestmark = pytest.mark.usefixtures('layout')


def au_at(name, aid, inst_id, inst_name, kind, pos='middle'):
    """An authorship credited to another institution only (no school)."""
    return dict(author_position=pos, raw_author_name=name, author=dict(id=OA + aid, display_name=name),
                institutions=[dict(id=OA + inst_id, display_name=inst_name, type=kind, lineage=[OA + inst_id])], raw_affiliation_strings=[inst_name])


def school(tmp_path, monkeypatch, sweep, periods_):
    ov = copy.deepcopy(T.OVERRIDES)
    ov[T.SCHOOL]['Ada Lovelace']['periods'] = periods_
    monkeypatch.setattr(T, 'OVERRIDES', ov)
    T.write_school(tmp_path, sweep)
    return T.run_stages(tmp_path, upto='papers')


def ev(q):
    return [T.src(q)]


A = dict(id='reviewed:ada:a', start='2015', end=None, asof='2015-08-07', evidence=ev('Ada Lovelace, Assistant Professor (captured 2015-08-07)'))
B = dict(id='reviewed:ada:b', start='2019', end=None, evidence=ev('Ada Lovelace, Professor (captured 2019)'))


def affiliated(wid, title, year, month='05'):
    w = work(wid, title, year, [au('Ada Lovelace', 'A1', pos='first'), au('Alan Turing', 'A9')])
    w['publication_date'] = f'{year}-{month}-01'
    return w


def test_R_PAP_28_bridge_periods_unit():
    full = {2016: 3, 2017: 1, 2018: 2}
    (b,) = periods.bridge_periods([A, B], full)
    assert (b['start'], b['end'], b['asof']) == ('2015-08-07', '2019', None) and len(b['evidence']) == 2
    assert periods.contains(b['start'], b['end'], '2017-05-01', None) == 'supported'
    assert periods.bridge_periods([A, B], {2016: 3, 2018: 2}) == []                      # 2017 has no school-affiliated work
    assert periods.bridge_periods([A, B], full, moved=True) == []                        # departure evidence
    assert periods.bridge_periods([dict(A, end='2016'), B], full) == []                  # A is not open
    moved = dict(A, evidence=[dict(T.src('left'), kind='faculty_end_moved')])
    assert periods.bridge_periods([moved, B], full) == []
    assert periods.bridge_periods([A, dict(B, start='2015')], full) == []                # no gap


def test_R_PAP_28_continuity_bridge_admits_gap_years(tmp_path, monkeypatch):
    sweep = [affiliated('W20', 'First Year Paper', 2015, '03'), affiliated('W21', 'Bridged Sixteen', 2016), affiliated('W22', 'Bridged Seventeen', 2017),
             affiliated('W23', 'Bridged Eighteen', 2018)]
    ctx = school(tmp_path, monkeypatch, sweep, [A, B])
    ada = T.rows_of(ctx, 'Ada Lovelace')
    assert ctx.n['continuity_bridge_periods'] == 1
    assert {'Bridged Sixteen', 'Bridged Seventeen', 'Bridged Eighteen'} <= set(ada)
    assert ada['Bridged Seventeen']['appointment']['periodId'].startswith('bridge_reviewed:ada:a__reviewed:ada:b')
    pi = {p['pi']: p for p in ctx.pis}['Ada Lovelace']
    assert any(q['id'].startswith('bridge_') and q['reviewed'].startswith('R-PAP-28') for q in pi['periods'])


def test_R_PAP_28_no_bridge_with_a_missing_year(tmp_path, monkeypatch):
    sweep = [affiliated('W21', 'Bridged Sixteen', 2016), affiliated('W23', 'Bridged Eighteen', 2018)]   # nothing in 2017
    ctx = school(tmp_path, monkeypatch, sweep, [A, B])
    assert ctx.n['continuity_bridge_periods'] == 0 and 'Bridged Sixteen' not in T.rows_of(ctx, 'Ada Lovelace')


def test_R_PAP_28_boundary_year_affiliated_paper_is_kept(tmp_path, monkeypatch):
    """A year-precision start cannot place a March paper against it; the paper's own Princeton affiliation settles it. An
    advisee-route paper in the same year does not get that."""
    sweep = [affiliated('W20', 'First Year Paper', 2015, '03'),
             work('W24', 'First Year Advisee Route', 2015, [au('Ada Lovelace', 'A1', school=False, pos='first'), au('Alan Turing', 'A9')])]
    sweep[1]['publication_date'] = '2015-03-01'
    ctx = school(tmp_path, monkeypatch, sweep, [A])
    ada = T.rows_of(ctx, 'Ada Lovelace')
    assert 'First Year Paper' in ada and ctx.n['period_boundary_affiliated'] == 1
    assert 'First Year Advisee Route' not in ada


def cross(company_kind='company', co_at_school=True, extra_same_year=2):
    own = [affiliated(f'W3{i}', f'Same Year Affiliated {i}', 2020) for i in range(extra_same_year)]
    byline = [au_at('Ada Lovelace', 'A1', 'I99', 'Nvidia', company_kind, pos='first'),
              au('Dave Danskin', 'A55') if co_at_school else au_at('Dave Danskin', 'A55', 'I98', 'Elsewhere', 'company')]
    return own + [work('W40', 'Selective Caches for Hybrid Memory', 2020, byline, doi='10.5/w40')]


@pytest.mark.parametrize('kw,kept', [({}, True), ({'company_kind': 'education'}, False), ({'co_at_school': False}, False), ({'extra_same_year': 1}, False)])
def test_R_PAP_29_cross_affiliated_byline(tmp_path, monkeypatch, kw, kept):
    ctx = school(tmp_path, monkeypatch, cross(**kw), [T.OVERRIDES[T.SCHOOL]['Ada Lovelace']['periods'][0]])
    row = T.rows_of(ctx, 'Ada Lovelace').get('Selective Caches for Hybrid Memory')
    assert bool(row) is kept
    if kept:
        assert row['authorship']['school_via'][0].startswith('cross-affiliated byline') and ctx.n['school_via_cross_affiliation'] == 1
    else:
        assert ctx.n['school_via_cross_affiliation'] == 0
