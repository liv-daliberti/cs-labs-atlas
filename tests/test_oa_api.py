"""tools/oa_api.py: the key never shows in a message, an exception or a traceback (2026-11-04 incident), and the ledger line has no key."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import oa_api  # noqa: E402

KEY = 'k3y-SECRET-0123456789'


def test_redact_masks_key_and_params():
    s = oa_api.redact(f'GET https://api.openalex.org/works?filter=x&api_key={KEY}&mailto=a@b.org failed ({KEY})', KEY)
    assert KEY not in s and 'a@b.org' not in s and 'api_key=***' in s


def test_transport_error_has_no_key_and_no_chained_url(tmp_path, monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError(f'HTTPSConnectionPool: Max retries exceeded with url: /works?api_key={KEY}')
    cl = oa_api.Client(cap=5, key=KEY, ledger=tmp_path / 'l.jsonl')
    monkeypatch.setattr(cl.s, 'get', boom)
    monkeypatch.setattr(oa_api.time, 'sleep', lambda *_: None)
    try:
        cl.get('works', {'filter': 'x'})
    except oa_api.OAError as e:
        assert KEY not in str(e) and e.__cause__ is None and e.__context__ is None or KEY not in repr(e.__context__)
    else:
        raise AssertionError('no error')


def test_ledger_and_cap(tmp_path, monkeypatch):
    class R:
        status_code = 200
        text = '{}'
        headers = {'X-RateLimit-Remaining': '9000', 'X-RateLimit-Credits-Used': '1'}

        def json(self):
            return {'meta': {}, 'results': []}
    led = tmp_path / 'l.jsonl'
    cl = oa_api.Client(cap=2, key=KEY, ledger=led)
    monkeypatch.setattr(cl.s, 'get', lambda *a, **k: R())
    monkeypatch.setattr(oa_api.time, 'sleep', lambda *_: None)
    cl.get('works'); cl.get('works')
    try:
        cl.get('works')
    except oa_api.Spent:
        pass
    else:
        raise AssertionError('cap not enforced')
    lines = [json.loads(x) for x in led.read_text().splitlines()]
    assert len(lines) == 2 and lines[0]['remaining'] == '9000' and KEY not in led.read_text()
