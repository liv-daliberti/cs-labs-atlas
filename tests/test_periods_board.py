"""Stage 4 (ETH, 2026-11-25): Board entries as dated period evidence, and a fetch narrowed to the PIs still needed."""
import json

import periods_school as PS


def lists(tmp_path, monkeypatch, entries):
    f = tmp_path / 'official-lists.json'
    f.write_text(json.dumps(entries))
    monkeypatch.setattr(PS.P, 'data', lambda name, key=None: tmp_path / name)
    return f


def entry(name, date, quote, kind='board_appointment', inst='ETH Zurich'):
    return dict(list=kind, name=name, url='https://ethrat.ch/x', sha256='a' * 64, date=date, rank=None, quote=quote, institution=inst)


NEW = 'Professor Ada Lovelace (*1980), currently Associate Professor at EPFL, as Full Professor of Computer Science.'
PROMO = 'Professor Ada Lovelace (*1980), currently Associate Professor at ETH Zurich, as Full Professor of Computer Science.'


def test_new_appointment_dates_the_start_for_a_still_listed_pi(tmp_path, monkeypatch):
    lists(tmp_path, monkeypatch, [entry('Ada Lovelace', '20180301', NEW)])
    out = PS.board_periods('ethz', {'Ada Lovelace': []}, {'Ada Lovelace': 2026})
    assert out['Ada Lovelace']['facultyStart'] == '2018-03-01' and out['Ada Lovelace']['facultyEnd'] is None


def test_promotion_proves_a_year_but_dates_no_start(tmp_path, monkeypatch):
    lists(tmp_path, monkeypatch, [entry('Ada Lovelace', '20200301', PROMO)])
    assert PS.board_periods('ethz', {'Ada Lovelace': []}, {'Ada Lovelace': 2026}) == {}
    assert PS.board_proven_years('ethz', 'Ada Lovelace') == {2020}


def test_departed_pi_without_retirement_gets_no_period(tmp_path, monkeypatch):
    lists(tmp_path, monkeypatch, [entry('Ada Lovelace', '20180301', NEW)])
    assert PS.board_periods('ethz', {'Ada Lovelace': []}, {'Ada Lovelace': 2021}) == {}


def test_retirement_closes_the_period_and_epfl_entries_do_not_count(tmp_path, monkeypatch):
    lists(tmp_path, monkeypatch, [entry('Ada Lovelace', '20180301', NEW), entry('Ada Lovelace', '20240301', 'is to retire at the end of July 2024.', 'board_retirement'),
                                  entry('Bob Babbage', '20190101', NEW, inst='EPFL')])
    out = PS.board_periods('ethz', {'Ada Lovelace': [], 'Bob Babbage': []}, {'Ada Lovelace': 2023, 'Bob Babbage': 2026})
    assert out['Ada Lovelace']['facultyEnd'] == '2024-03-01' and 'Bob Babbage' not in out


def test_excluded_names_come_from_the_overrides(monkeypatch):
    monkeypatch.setattr(PS.CO, 'section', lambda key: {'A': {'exclude': True}, 'B': {'home_department': 'x'}})
    assert PS.excluded_names('ethz') == {'A'}


def test_fetch_needed_skips_excluded_settled_and_honours_an_explicit_list(tmp_path, monkeypatch):
    import stage_gate as G
    monkeypatch.setattr(PS.P, 'data', lambda name, key=None: tmp_path / name)
    monkeypatch.setattr(PS, 'board_merge', lambda key, per: per)
    monkeypatch.setattr(PS.CO, 'section', lambda key: {'Excl': {'exclude': True}})
    monkeypatch.setattr(G, 'pis_of', lambda key: [{'name': n} for n in ('Excl', 'Settled', 'Open1', 'Open2')])
    monkeypatch.setattr(G, 'period_basis', lambda key, x, have, ov: 'contiguous_listings' if x['name'] == 'Settled' else None)
    assert PS.fetch_needed('ethz') == {'Open1', 'Open2'}
    assert PS.fetch_needed('ethz', only=['Open2', 'Excl']) == {'Open2'}


def test_d0080_bridges_only_department_wide_gaps_for_a_pi_listed_before_and_after():
    rows = [dict(name='A', dept='INFK', kind='main', year=y) for y in (2016, 2019)] + [dict(name='B', dept='INFK', kind='main', year=2016)] + \
           [dict(name='C', dept='INFK', kind='main', year=y) for y in (2018, 2019)]
    table = {'INFK': {2017: {'pages': []}}}
    # A is listed before (2016) and after (2019) the department-wide gap 2017: bridged
    assert PS.interpolated_years('x', 'A', [], [2017], table, rows) == {2017: 'INFK'}
    # a year that is not a department-wide gap (the listing exists and omits the PI) is never bridged
    assert PS.interpolated_years('x', 'A', [], [2018], table, rows) == {}
    # B has no listing after the gap, C none before it
    assert PS.interpolated_years('x', 'B', [], [2017], table, rows) == {}
    assert PS.interpolated_years('x', 'C', [], [2017], table, rows) == {}
    # a Board retirement by then (a departure) stops the bridge
    assert PS.interpolated_years('x', 'A', [], [2017], table, rows, {2017}) == {}


def test_d0080_does_not_bridge_a_department_switch():
    rows = [dict(name='M', dept='INFK', kind='main', year=2016), dict(name='M', dept='ITET', kind='main', year=2022)]
    table = {'INFK': {2020: {'pages': []}}, 'ITET': {2020: {'pages': []}}}
    assert PS.interpolated_years('x', 'M', [], [2020], table, rows) == {}
