"""convert keeps an unchanged row's converted_on, so re-running the chain does not make the excluded-unresolved audit stale."""
import json

from tools import excluded_audit as EA


def pending(name, **kw):
    d = dict(name=name, aliases=[], source='dblp_affiliation', decision='pending_source_coverage', reason='no source places the person',
             units_searched=['CS_MAIN roster 2016-2026'])
    d.update(kw)
    return d


def run(tmp_path, monkeypatch, rows, today):
    class D(EA.datetime.date):
        @classmethod
        def today(cls):
            return cls.fromisoformat(today)
    monkeypatch.setattr(EA.P, 'data', lambda name, key: tmp_path / name)
    monkeypatch.setattr(EA.datetime, 'date', D)
    (tmp_path / 'cs-related-review.json').write_text(json.dumps(dict(decisions=rows)))
    EA.convert('k')
    return {d['name']: d for d in json.loads((tmp_path / 'cs-related-review.json').read_text())['decisions']}


def test_unchanged_row_keeps_its_date_and_changed_row_is_restamped(tmp_path, monkeypatch):
    first = run(tmp_path, monkeypatch, [pending('A'), pending('B')], '2026-11-24')
    assert first['A']['converted_on'] == first['B']['converted_on'] == '2026-11-24'
    second = run(tmp_path, monkeypatch, [pending('A'), pending('B', reason='a new source was tried')], '2026-11-25')
    assert second['A']['converted_on'] == '2026-11-24'          # unchanged: keeps the stamp
    assert second['B']['converted_on'] == '2026-11-25'          # changed: restamped
    assert EA.fingerprint(second['A']) == EA.fingerprint(first['A'])   # so the audit's population fingerprint still matches
    third = run(tmp_path, monkeypatch, [pending('A'), pending('B', reason='a new source was tried'), pending('C')], '2026-11-26')
    assert third['B']['converted_on'] == '2026-11-25' and third['C']['converted_on'] == '2026-11-26'
