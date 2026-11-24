"""A school without the optional PI-work cache still emits its required report count."""
import json

import atlas_paths as P
import provenance
import test_build_rules as T
from pihier import build


def test_report_serializes_zero_without_optional_pi_work_cache(tmp_path, monkeypatch, layout):
    T.write_school(tmp_path)
    assert not P.data('pi-works.sqlite', T.SCHOOL, root=tmp_path).exists()
    ctx = T.run_stages(tmp_path)
    assert 'pi_work_list_hits' not in ctx.n
    ctx.out.mkdir()
    monkeypatch.setattr(provenance, 'block', lambda school: {})
    build.write(ctx)
    report = json.loads((ctx.out / 'report.json').read_text())
    assert report['counts']['pi_work_list_hits'] == 0
    assert report['counts']['sweep_name_hits'] > 0
