"""periods_school.gaps saves each PI as it completes and resumes (2026-11-18: a 58-minute Wayback run timed out and lost every PI)."""
import json
import re

import periods_school as PS  # noqa: E402
import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402
import school_config as S  # noqa: E402
import stage_gate as SG  # noqa: E402
import census_overrides as CO  # noqa: E402
import cs_related_school as CR  # noqa: E402


def setup(tmp_path, monkeypatch):
    pis = [{'name': 'A One', 'years_listed': [2016, 2018], 'is_pi': True}, {'name': 'B Two', 'years_listed': [2016, 2018], 'is_pi': True}]
    (tmp_path / 'census-faculty.json').write_text(json.dumps(pis))
    monkeypatch.setattr(P, 'data', lambda name, school=None, root=None, layout=None: tmp_path / name)
    monkeypatch.setattr(P, 'data_w', lambda name, school=None, root=None, layout=None: tmp_path / name)
    monkeypatch.setattr(PS, 'targets', lambda key: [{'name': p['name'], 'urls': ['https://x.edu/' + p['name'][0]]} for p in pis])
    monkeypatch.setattr(W, 'con', lambda key: None)
    monkeypatch.setattr(S, 'aff_rx', lambda key: re.compile('x'))
    monkeypatch.setattr(S, 'get', lambda key: {})
    monkeypatch.setattr(S, 'field', lambda cfg, f, d=None: [])
    monkeypatch.setattr(SG, 'span_gaps', lambda x: [2017])
    calls = []
    monkeypatch.setattr(W, 'cdx_rows', lambda c, k, frm, to, collapse: calls.append(k) or [{'timestamp': '20170601000000', 'original': k}])
    monkeypatch.setattr(W, 'capture', lambda c, ts, orig, u, why: ('cap', 200, 'sha', b'x'))
    monkeypatch.setattr(W, 'flat', lambda b: 'x')
    monkeypatch.setattr(CR, 'faculty_evidence', lambda pages, names: [{'ladder': True, 'quote': 'Professor'}])
    saved = {}
    monkeypatch.setattr(CO, 'open_section', lambda key: (saved, lambda: None))
    return calls, saved


def test_saves_per_pi_and_resumes(tmp_path, monkeypatch):
    calls, saved = setup(tmp_path, monkeypatch)
    PS.gaps('x', write=True, max_pis=1)
    out = json.loads((tmp_path / 'gap-year-evidence.json').read_text())
    assert list(out) == ['A One'] and out['A One']['closed']          # saved after the first PI, before the run ended
    assert 'A One' in saved and saved['A One']['periods']              # and its period was written at once
    n = len(calls)
    PS.gaps('x', write=True)
    out = json.loads((tmp_path / 'gap-year-evidence.json').read_text())
    assert set(out) == {'A One', 'B Two'}
    assert len(calls) == n + 1                                        # A One was not searched again
