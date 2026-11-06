"""R-PAP-37 (listing continuity: Gorodetsky's 2021-2026 papers at Michigan, the Chen and Aksoy student links), 2026-11-05, on the
synthetic school of test_build_rules. Fixtures only."""
import copy
import json

import pytest

import test_build_rules as T
from pihier import periods

OA, au, work = T.OA, T.au, T.work
pytestmark = pytest.mark.usefixtures('layout')
from pihier import papers as _papers

L18 = dict(year=2018, url='https://web.archive.org/web/20180423190308id_/https://aero.example.edu/people/', sha256='a' * 64,
           quote='Ada Lovelace Assistant Professor', kind='unit_listing:AERO')
L20 = dict(L18, year=2020, url='https://web.archive.org/web/20200617030240id_/https://aero.example.edu/people/')
L17 = dict(L18, year=2017, url='https://web.archive.org/web/20170423190308id_/https://aero.example.edu/people/')
P0 = dict(listings=[L17, L20], periods=[], listingsAfterMove=[])   # interior gap 2018-2019 is never qualified by D below unless stated


def tail(*a, **k):
    return [q for q in periods.listing_bridge_periods(*a, **k) if q['id'].endswith('_tail')]

D = {y: 1 for y in range(2019, 2027)}


def test_R_PAP_37_tail_runs_from_the_last_listing_to_today():
    (t,) = tail(P0, D, {}, {}, today='2026-11-05')
    assert (t['start'], t['end'], t['asof'], t['reviewed']) == ('2020-06-17', None, '2026-11-05', periods.LISTING_BRIDGE)
    assert periods.contains(t['start'], t['end'], '2024-03-26', t['asof']) == 'supported'
    assert t['evidence'][0]['sha256'] == L20['sha256'] and t['years'] == [2021, 2026]


def test_R_PAP_37_tail_stops_at_the_first_year_without_a_school_named_work():
    (t,) = tail(P0, {2021: 2, 2022: 1, 2024: 3}, {}, {}, today='2026-11-05')
    assert (t['end'], t['years']) == ('2022-12-31', [2021, 2022])        # 2023 names nothing: the run ends, 2024 is not reached
    assert tail(P0, {2022: 1}, {}, {}, today='2026-11-05') == []   # the year right after names nothing


def test_R_PAP_37_one_listing_year_bridges_nothing():
    assert periods.listing_bridge_periods(dict(P0, listings=[L20]), D, {}, {}, today='2026-11-05') == []


def test_R_PAP_37_interior_gap_needs_every_year():
    p = dict(P0, listings=[L18, dict(L20, year=2021, url='https://web.archive.org/web/20210617030240id_/https://aero.example.edu/people/')])
    (i,) = periods.listing_bridge_periods(p, {2019: 1, 2020: 1}, {}, {}, today='2019-06-01')
    assert (i['start'], i['end']) == ('2018-04-23', '2021-06-17') and i['years'] == [2019, 2020]
    assert periods.listing_bridge_periods(p, {2019: 1}, {}, {}, today='2019-06-01') == []


def test_R_PAP_37_no_head():
    # nothing before the first listing is bridged: the arrival side is R-PAP-13's
    assert all(q['start'] >= '2018' for q in tail(P0, {**D, 2016: 5, 2017: 5}, {}, {}))


def test_R_PAP_37_guards():
    assert tail(P0, D, {}, {}, moved=True) == []                                     # departure evidence
    assert tail(dict(P0, listingsAfterMove=[L20]), D, {}, {}) == []
    assert tail(dict(P0, periods=[dict(id='r')]), D, {}, {}) == []                  # a period is R-PAP-28's
    for q in ('Ada Lovelace Professor (courtesy)', 'Ada Lovelace Adjunct Professor', 'Ada Lovelace Professor Emeritus', 'Ada Lovelace, visiting'):
        assert tail(dict(P0, listings=[L18, dict(L20, quote=q)]), D, {}, {}) == []   # not a primary appointment
    assert tail(P0, D, {2021: 2}, {}, today='2026-11-05') == []                   # another institution more often in the first year
    assert tail(P0, D, {2023: 2}, {}, today='2026-11-05')[0]['years'] == [2021, 2022]


def test_R_PAP_37_a_listing_drop_closes_the_period():
    dept = dict(L20, kind='dept_listing:CSE')
    p = dict(P0, listings=[L18, dept])
    # the department's listing was captured in 2022 and omits the PI: the run ends before it; no coverage data for the department: nothing
    (t,) = tail(p, D, {}, {'CSE': {2022, 2023}}, today='2026-11-05')
    assert t['years'] == [2021, 2021]
    assert tail(p, D, {}, {}, today='2026-11-05') == []


def aff(wid, title, year, pos='first'):
    w = work(wid, title, year, [au('Ada Lovelace', 'A1', pos=pos), au('Alan Turing', 'A9')])
    w['publication_date'] = f'{year}-05-01'
    return w


def school(tmp_path, monkeypatch, sweep, covered=None, listing_years=(2017, 2018), on=True):
    monkeypatch.setattr(_papers, 'listing_continuity_on', lambda s: on)
    ov = copy.deepcopy(T.OVERRIDES)
    ov[T.SCHOOL]['Ada Lovelace']['periods'] = []
    monkeypatch.setattr(T, 'OVERRIDES', ov)
    ls = [dict(pi='Ada Lovelace', year=y, capture_url=f'https://web.archive.org/web/{y}0301000000/https://cs.example.edu/people', sha256=T.SHA,
               quote='Ada Lovelace Associate Professor', rank_as_listed='Associate Professor', department='Computer Science') for y in listing_years]
    monkeypatch.setattr(T, 'LISTINGS', ls)
    T.write_school(tmp_path, sweep)
    T.put(tmp_path, 'coverage.json').write_text(json.dumps(covered if covered is not None else {'Computer Science': {'2018': {'all faculty H1': 'ok'}}}))
    return T.run_stages(tmp_path, upto='papers')


def test_R_PAP_37_build_admits_direct_papers_after_the_last_listing(tmp_path, monkeypatch):
    sweep = [aff('W20', 'Listed Year', 2018), aff('W21', 'After One', 2019), aff('W22', 'After Two', 2020)]
    unaff = work('W23', 'Unaffiliated After', 2020, [au('Ada Lovelace', 'A1', school=False), au('Alan Turing', 'A9')])
    unaff['publication_date'] = '2020-06-01'
    ctx = school(tmp_path, monkeypatch, sweep + [unaff])
    ada = T.rows_of(ctx, 'Ada Lovelace')
    assert ctx.n['listing_bridge_periods'] == 1
    assert {'Listed Year', 'After One', 'After Two'} <= set(ada)
    assert ada['After Two']['appointment']['periodId'].startswith('listing_bridge_2018_tail')
    assert 'Unaffiliated After' not in ada                                   # only the PI's own byline naming the school counts


def test_R_PAP_37_build_listing_drop_stops_the_bridge(tmp_path, monkeypatch):
    sweep = [aff('W20', 'Listed Year', 2018), aff('W21', 'After One', 2019), aff('W22', 'After Two', 2020)]
    cov = {'Computer Science': {'2018': {'all faculty H1': 'ok'}, '2020': {'all faculty H1': 'ok'}}}      # 2020 was captured and lacks her
    ada = T.rows_of(school(tmp_path, monkeypatch, sweep, covered=cov), 'Ada Lovelace')
    assert 'After One' in ada and 'After Two' not in ada


def test_R_PAP_37_is_off_unless_the_charter_turns_it_on(tmp_path, monkeypatch):
    sweep = [aff('W20', 'Listed Year', 2018), aff('W21', 'After One', 2019)]
    ctx = school(tmp_path, monkeypatch, sweep, on=False)
    assert ctx.n['listing_bridge_periods'] == 0 and 'After One' not in T.rows_of(ctx, 'Ada Lovelace')


def test_R_PAP_37_charters():
    import pathlib
    import school_config as S
    root = pathlib.Path(__file__).resolve().parents[1] / 'schools'
    on = {f.stem for f in root.glob('*.toml') if f.stem != 'TEMPLATE' and S.field(S._toml.loads(f.read_text()), 'rules.listing_continuity')}
    assert 'michigan' in on and on <= {'michigan', 'gatech', 'uchicago', 'mit', 'cmu', 'berkeley'}
