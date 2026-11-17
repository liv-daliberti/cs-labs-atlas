"""downloads_ready (R3c): the catalogue and loop need gates 0-2, a fresh build and, per PI, a settled window and identity; never the stage 3-8 audits."""
import gzip
import json
import os

import downloads_ready as DR
import loop_starter as L
import stage_gate as SG


def pi(name, years=(2020, 2021, 2022), **kw):
    return dict(name=name, years_listed=list(years), **kw)


def test_period_and_identity_basis():
    assert SG.period_basis('x', pi('A'), set(), {}) == 'contiguous_listings'
    assert SG.period_basis('x', pi('A', years=(2019, 2022)), set(), {}) is None   # a gap with no review
    assert SG.period_basis('x', pi('A', years=(2019, 2022)), {'A'}, {}) == 'period'
    ov = {'A': dict(unproven_years=[2020, 2021], why_unproven='searched')}
    assert SG.period_basis('x', pi('A', years=(2019, 2022)), set(), ov) == 'gap_reviewed_unproven'
    assert SG.period_basis('x', pi('A', years=()), set(), {}) is None
    assert SG.identity_basis(pi('A', dblp='a/b'), {}) == 'dblp'
    assert SG.identity_basis(pi('A'), dict(orcid='0000')) == 'orcid'
    assert SG.identity_basis(pi('A'), dict(no_identity=True, why_no_identity='searched')) == 'reviewed_no_identity'
    assert SG.identity_basis(pi('A'), dict(no_identity=True)) is None


def status(**held):
    return {n: dict(name=n, period='period', identity='dblp', reasons=r) for n, r in held.items()}


def test_row_hold_is_per_pi():
    st = status(A=[], B=['no identity anchor'])
    row = lambda p, **k: dict(pi=p, appointment={'listing': {}}, **k)  # noqa: E731
    assert DR.row_hold(st, row('A')) is None
    assert 'identity' in DR.row_hold(st, row('B'))
    assert 'not a census PI' in DR.row_hold(st, row('Z'))
    assert DR.row_hold(st, dict(pi='A', appointment=None)) == 'row has no appointment record'   # never a paper outside the window
    assert [r['pi'] for r in map(row, 'AB') if DR.keep('x', st)(r)] == ['A']


def build(tmp_path, monkeypatch, gates='pass', newer=None):
    d = tmp_path / 'h'
    d.mkdir(exist_ok=True)
    for n in DR.OUTPUTS:
        (d / n).write_text('x')
        os.utime(d / n, (1000, 1000))
    for n in DR.SETTLE_INPUTS:
        (d / n).write_text('x')
        os.utime(d / n, (500, 500))
    for n in ('lab-websites.json', 'labpage-audit.jsonl.gz', 'students.json', 'labpage-acceptance.json'):   # stage 3/6/7 files: newer than the build, must not block
        (d / n).write_text('x')
        os.utime(d / n, (9999, 9999))
    if newer:
        os.utime(d / newer, (2000, 2000))
    monkeypatch.setattr(DR.P, 'data', lambda n, k=None: d / n)
    monkeypatch.setattr(DR.SG, 'evaluate', lambda key, g: dict(gate=gates, open=1, items=['x']))
    return d


def test_school_blockers(tmp_path, monkeypatch):
    build(tmp_path, monkeypatch)
    assert DR.school_blockers('x') == []   # audit and student files newer than the build do not block


def test_stale_build_and_failed_gate(tmp_path, monkeypatch):
    build(tmp_path, monkeypatch, newer='faculty-periods.json')
    assert any('faculty-periods.json' in b for b in DR.school_blockers('x'))
    build(tmp_path, monkeypatch, gates='fail')
    assert any(b.startswith('gate 0 fails') for b in DR.school_blockers('x'))


def test_readiness_holds_pis(tmp_path, monkeypatch):
    d = build(tmp_path, monkeypatch)
    rows = [dict(pi='A', appointment={'listing': {}}), dict(pi='B', appointment={'listing': {}}), dict(pi='B', appointment={'listing': {}})]
    with gzip.open(d / 'lab_papers.jsonl.gz', 'wt') as f:
        f.write(''.join(json.dumps(r) + '\n' for r in rows))
    st = status(A=[], B=['no identity anchor'])
    monkeypatch.setattr(DR, 'pi_status', lambda key: st)
    r = DR.readiness('x')
    assert r['ready'] and (r['rows'], r['rows_ready'], r['rows_held']) == (3, 1, 2) and list(r['held']) == ['B']


def test_loop_starter_early_needs_record(tmp_path, monkeypatch):
    s = tmp_path / 'st'
    s.mkdir()
    (s / '.copy-quality-warm.json').write_text('{}')
    monkeypatch.setattr(DR, 'start_blocker', lambda k: 'downloads-ready: not ready')
    assert L.ready('x', s, set(), tmp_path, early=True) == 'downloads-ready: not ready'
    assert L.ready('x', s, set(), tmp_path) is None   # without --early nothing changes
    monkeypatch.setattr(DR, 'start_blocker', lambda k: None)
    assert L.ready('x', s, set(), tmp_path, early=True) is None


def test_start_blocker(tmp_path, monkeypatch):
    d = build(tmp_path, monkeypatch)
    monkeypatch.setattr(DR.P, 'HIERARCHY', str(tmp_path))
    (tmp_path / 'x' / 'reports').mkdir(parents=True)
    assert DR.start_blocker('x') == 'no downloads-ready record'
    DR.record('x', dict(ready=True), catalogue_added=False)
    assert 'add_works' in DR.start_blocker('x')
    DR.record('x', dict(ready=True), catalogue_added=True)
    f = tmp_path / 'x' / 'reports' / 'downloads-ready.json'
    os.utime(f, (3000, 3000))
    assert DR.start_blocker('x') is None
    os.utime(f, (500, 500))
    assert 'older than the build' in DR.start_blocker('x')
    assert d.exists()
