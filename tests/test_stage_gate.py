"""ROADMAP #39: stage_gate gates for stages 0 and 6-10, waivers, ISO periods, and `--run` (steps up to the first review step, never on a released school)."""
import json
from types import SimpleNamespace

import pytest

import atlas_paths as P
import stage_gate as G


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Every P.data(name, key) goes under tmp_path/<key>/<name>; S.get returns a per-test charter."""
    cfg = {'status': 'onboarding', 'window': [2016, 2026], 'departments': []}
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    monkeypatch.setattr(G.S, 'get', lambda key: cfg)
    monkeypatch.setattr(G.S, 'check', lambda key: [])
    monkeypatch.setattr(P, 'HIERARCHY', tmp_path)
    (tmp_path / 'u').mkdir()
    (tmp_path / '_').mkdir()
    monkeypatch.setattr(G, 'ACCURACY_DIR', tmp_path / 'acc')
    (tmp_path / 'acc').mkdir()
    return SimpleNamespace(root=tmp_path, cfg=cfg, put=lambda name, obj, key='u': (tmp_path / key / name).write_text(json.dumps(obj)))


def test_gate0_needs_hosts_json_and_consistent_hosts(tree):
    assert G.evaluate('u', 0)['gate'] == 'fail'
    tree.put('hosts.json', {'hosts': [{'host': 'a', 'consistent': False, 'problems': ['probe challenged']}]})
    r = G.evaluate('u', 0)
    assert r['gate'] == 'fail' and 'probe challenged' in r['items'][0]
    tree.put('hosts.json', {'hosts': [{'host': 'a', 'consistent': True}]})
    assert G.evaluate('u', 0)['gate'] == 'pass'


def test_gate8_local_share_and_ledger(tree):
    tree.put('copies.json', {'summary': {'lab_papers': 100, 'local': 80}})
    r = G.evaluate('u', 8)
    assert r['gate'] == 'fail' and r['local_share'] == 0.8 and len(r['items']) == 2
    tree.put('copies.json', {'summary': {'lab_papers': 100, 'local': 90}})
    tree.put('unavailable-summary.json', {})   # an empty summary is still a missing ledger
    assert G.evaluate('u', 8)['gate'] == 'fail'
    tree.put('unavailable-summary.json', {'school': 'u'})
    assert G.evaluate('u', 8)['gate'] == 'pass'


def test_gate9_thresholds_and_stale_build(tree):
    good = {'lab_precision_uniform': {'p': .96}, 'student_precision_uniform': {'p': 1.0}, 'lab_coverage': {'p': .9}, 'files': {'a': 1}, 'files_now': {'a': 1}}
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(good))
    assert G.evaluate('u', 9)['gate'] == 'pass'
    bad = dict(good, lab_precision_uniform={'p': .92}, files_now={'a': 2})
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(bad))
    r = G.evaluate('u', 9)
    assert r['gate'] == 'fail' and r['open'] == 2


def test_waiver_needs_a_reason_and_keeps_the_items(tree):
    tree.put('copies.json', {'summary': {'lab_papers': 10, 'local': 1}})
    tree.put('gate-exceptions.json', {'8': {'reason': '', 'by': 'owner'}})
    assert G.evaluate('u', 8)['gate'] == 'fail'
    tree.put('gate-exceptions.json', {'8': {'reason': 'owner shipped it 2026-11-02', 'by': 'owner'}})
    r = G.evaluate('u', 8)
    assert r['gate'] == 'waived' and r['open'] == 2 and r['waiver']['by'] == 'owner'


def test_gate10_needs_release_status_and_manifest(tree, monkeypatch):
    rel = tree.root / 'rel' / 'latest'
    rel.mkdir(parents=True)
    monkeypatch.setattr(P, 'RELEASES', tree.root / 'rel')
    assert G.evaluate('u', 10)['open'] == 2
    tree.cfg['status'] = 'released'
    (rel / 'MANIFEST.json').write_text(json.dumps({'counts': {'u': {}}}))
    assert G.evaluate('u', 10)['gate'] == 'pass'


def test_gate4_flags_compact_dates(tree):
    tree.put('census-faculty.json', {'faculty': [{'name': 'A', 'is_pi': True, 'years_listed': [2016, 2017]}]})
    tree.put('census-overrides.json', {}, key='_')
    tree.put('faculty-periods.json', [{'name': 'A', 'facultyStart': '20261029', 'facultyEnd': None}])
    r = G.evaluate('u', 4)
    assert r['gate'] == 'fail' and 'ISO' in r['items'][0]
    tree.put('faculty-periods.json', [{'name': 'A', 'facultyStart': '2016', 'facultyEnd': '2026-10-29'}])
    assert G.evaluate('u', 4)['gate'] == 'pass'


def test_every_step_is_well_formed_and_every_stage_has_a_gate():
    assert set(G.STEPS) == set(G.GATES)
    for stage, steps in G.STEPS.items():
        assert len({s['name'] for s in steps}) == len(steps)
        assert steps[-1]['kind'] in ('hand', 'slurm', 'local')
        for s in steps:
            assert s['kind'] in ('local', 'slurm', 'hand')
            if s['kind'] == 'local':
                assert (G.CODE / s['script']).exists(), s
            if s['kind'] == 'slurm':
                assert s['cmd'].startswith(('PY ', 'bash ')) and s['py'] in ('project', 'collector')
            for n in s.get('done') or []:
                P.data(n, 'x') if '{school}' in P._DATA[n][1] else P.data(n)


def test_run_refuses_a_released_school(tree):
    tree.cfg['status'] = 'released'
    with pytest.raises(SystemExit) as e:
        G.main(['u', '3', '--run'])
    assert 'never writes released data' in str(e.value)


def test_run_stops_at_the_first_review_step_and_skips_finished_steps(tree):
    calls = []

    def fake(argv, cwd=None):
        calls.append(argv)
        return SimpleNamespace(returncode=0)
    tree.put('hosts.json', {'hosts': []})   # stage 0's first step already ran
    status, log = G.run_stage('u', 0, run=fake)
    assert [e['result'] for e in log][:1] == ['done (output exists)']
    assert status == 'submitted' or status == 'review'
    assert log[1]['step'] == 'sweep' and log[1]['result'].startswith('slurm (not submitted')
    assert not calls   # nothing local was left to run


def test_run_runs_local_steps_in_order_and_stops_on_failure(tree):
    rcs = iter([0, 3])
    seen = []

    def fake(argv, cwd=None):
        seen.append(argv[2].rsplit('/', 1)[-1])
        return SimpleNamespace(returncode=next(rcs))
    status, log = G.run_stage('u', 2, run=fake)   # census, candidates, (slurm), cross-check, hand
    assert seen == ['census_build.py', 'cs_related_school.py'] and status == 'failed' and log[-1]['result'] == 'failed rc=3'


def test_shared_writers_need_allow_shared(tree):
    status, log = G.run_stage('u', 3, run=lambda *a, **k: SimpleNamespace(returncode=0))
    assert log[0]['step'] == 'homes' and 'allow-shared' in log[0]['result']


def test_dry_run_runs_nothing_and_writes_no_receipt(tree, capsys):
    G.main(['u', '2', '--run', '--dry-run'])
    assert not (tree.root / 'u' / 'reports').exists()
    assert 'dry run' in capsys.readouterr().out


def test_run_submits_the_slurm_steps_as_one_chain(tree, monkeypatch):
    import atlas_pipeline as AP
    got = {}
    monkeypatch.setattr(AP, 'submit', lambda name, schools, **k: got.update(name=name, schools=schools, **k) or {'sweep': '11'})
    (tree.root / 'u' / 'hosts.json').write_text('{"hosts": []}')
    status, log = G.run_stage('u', 0, submit=True, run=lambda *a, **k: SimpleNamespace(returncode=0))
    assert status == 'submitted' and got['name'] == 'stage0-u' and got['schools'] == ['u'] and got['guard_preempt'] is True
    assert got['stages'][0][:3] == ('sweep', 'school', 'PY $TOOLS/sweep_school.py {school}')
