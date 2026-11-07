"""arxiv.org direct fetches (owner 2026-11-06): opt-in candidate rows, a 15 s shared clock, stop on 403/429."""
import sys
from pathlib import Path

import ftp_common as F
import host_throttle as HT

ROOT = Path(__file__).resolve().parents[1]


def _bulk(monkeypatch, direct):
    import arxiv_bulk
    monkeypatch.setattr(arxiv_bulk, 'listing', lambda ids: {i: None for i in ids}, raising=False)
    sys.modules['arxiv_bulk'] = arxiv_bulk
    if direct:
        monkeypatch.setenv('ARXIV_DIRECT', '1')
    else:
        monkeypatch.delenv('ARXIV_DIRECT', raising=False)
    return F.bulk_rows({'w1': '2610.01234', 'w2': 'math/0301001'}, 'x')


def test_direct_rows_only_when_opted_in_and_only_pdf(monkeypatch):
    rows, missing = _bulk(monkeypatch, False)
    assert rows == [] and missing == 2
    rows, missing = _bulk(monkeypatch, True)
    assert [r['url'] for r in rows] == ['https://arxiv.org/pdf/2610.01234'] and rows[0]['landing_url'] == 'https://arxiv.org/abs/2610.01234' and missing == 1


def test_arxiv_is_on_the_shared_15_second_clock(tmp_path):
    assert HT.SHARED_INTERVAL['arxiv.org'] == 15.0
    p = tmp_path / 's.json'
    HT.reserve('arxiv.org', 1.0, now=100.0, path=p)
    assert HT.reserve('arxiv.org', 1.0, now=100.0, path=p) == 15.0


def test_wrapper_stops_arxiv_on_403_and_429():
    src = (ROOT / 'vendor' / 'cmu_tools' / 'collector_wrapper.py').read_text()
    assert "'arxiv.org': 15.0" in src
    assert "status_code == 403:\n            self.blocked['arxiv.org']" in src
    assert "key == 'arxiv.org' and value == RATE_429" in src


def test_blocked_arxiv_429_is_a_permanent_pause(tmp_path, monkeypatch):
    # Importing the collector monkeypatches the production client and can resolve
    # another checkout through its legacy sys.path setup. Exercise this checkout's
    # actual class in isolation, with a clock that rejects unintended sleeping.
    import ast
    from types import SimpleNamespace
    source = ast.parse((ROOT / 'vendor/cmu_tools/collector_wrapper.py').read_text())
    cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == '_Blocked')
    def unexpected_sleep(seconds):
        raise AssertionError(f'permanent pause attempted to sleep for {seconds}s')
    scope = {'HT': HT, 'time': SimpleNamespace(sleep=unexpected_sleep),
             'RATE_429': 'HTTP 429; retry later per server guidance'}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), '<collector _Blocked>', 'exec'), scope)
    monkeypatch.setenv('CS_ATLAS_THROTTLE_STATE', str(tmp_path / 'h.json'))
    b = scope['_Blocked']()
    b['arxiv.org'] = scope['RATE_429']
    assert 'arxiv.org' in b and 'stopped' in b['arxiv.org'] and 'arxiv.org' not in b._cool
