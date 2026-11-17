"""ROADMAP #39: stage_gate gates for stages 0 and 6-10, waivers, ISO periods, and `--run` (steps up to the first review step, never on a released school)."""
import json
from types import SimpleNamespace

import pytest

import atlas_paths as P
import stage_gate as G


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Every P.data(name, key) goes under tmp_path/<key>/<name>; S.get returns a per-test charter."""
    cfg = {'status': 'onboarding', 'window': [2016, 2026], 'departments': [], 'hosts': [{'host': 'a'}]}
    monkeypatch.setattr(P, 'data', lambda name, school=None, **k: tmp_path / (school or '_') / name)
    monkeypatch.setattr(G.S, 'get', lambda key: cfg)
    monkeypatch.setattr(G.S, 'check', lambda key: [])
    monkeypatch.setattr(G.S, 'inst', lambda key: 'I1')
    monkeypatch.setattr(G, 'snapshot_count', lambda key, root=None: 1)   # stage 0 also needs the snapshot (tests/test_stage_gate_stage0.py)
    monkeypatch.setattr(P, 'HIERARCHY', tmp_path)
    monkeypatch.setattr(G, 'traps_for', lambda key, stage: [])   # the trap checks have their own tests (tests/test_onboarding_traps.py)
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


def test_stage1_empty_legacy_charter_is_unmeasured_not_pass(tree):
    tree.cfg['status'] = 'released'
    r = G.evaluate('u', 1)
    assert r['gate'] == 'fail'
    assert r['departments'] == 0
    assert r['items'] == ['no Stage 1 departments in charter: faculty listing coverage is unmeasured']


def test_gate8_local_share_and_ledger(tree):
    tree.put('copies.json', {'summary': {'lab_papers': 100, 'local': 80}})
    r = G.evaluate('u', 8)
    assert r['gate'] == 'fail' and r['local_share'] == 0.8 and len(r['items']) == 1   # only the missing ledger: the 85% share is a target, not a gate
    assert r['copy_target_met'] is False
    tree.put('copies.json', {'summary': {'lab_papers': 100, 'local': 90}})
    tree.put('unavailable-summary.json', {})   # an empty summary is still a missing ledger
    assert G.evaluate('u', 8)['gate'] == 'fail'
    tree.put('unavailable-summary.json', {'school': 'u'})
    assert G.evaluate('u', 8)['gate'] == 'pass'


def test_gate9_thresholds_and_stale_build(tree):
    good = accuracy_summary(tree)
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(good))
    assert G.evaluate('u', 9)['gate'] == 'pass'
    bad = dict(good, lab_precision_uniform={'p': .92}, files_now=dict(good['files_now'], **{'pis.json': '0' * 64}))
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(bad))
    r = G.evaluate('u', 9)
    assert r['gate'] == 'fail' and r['open'] == 2


def test_R_ACC_01_gate9_compares_the_summary_hashes_with_the_live_build(tree):
    s = accuracy_summary(tree)
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(s))
    assert G.evaluate('u', 9)['gate'] == 'pass'
    (tree.root / 'u' / 'pis.json').write_text('[1, 2]')   # a rebuild after the draw; files == files_now (both stored at summarize time)
    r = G.evaluate('u', 9)
    assert r['gate'] == 'fail' and r['open'] == 1 and 'pis.json differ from the live files' in r['items'][0]


def accuracy_summary(tree):
    for name in G.ACCURACY_FILES:
        (tree.root / 'u' / name).write_text('[1]')
    files = {name: G.live_sha(tree.root / 'u' / name) for name in G.ACCURACY_FILES}
    return dict(lab_precision_uniform={'p': .96}, student_precision_uniform={'p': 1.0},
                lab_coverage={'p': .9}, files=files, files_now=dict(files))


@pytest.mark.parametrize('broken', ['absent', 'empty', 'partial', 'bad_hash', 'wrong_type', 'unknown_file'])
def test_accuracy_cannot_pass_without_complete_well_formed_live_build_bindings(tree, broken):
    summary = accuracy_summary(tree)
    for field in ('files', 'files_now'):
        if broken == 'absent':
            summary.pop(field)
        elif broken == 'empty':
            summary[field] = {}
        elif broken == 'partial':
            summary[field].pop('copies.json')
        elif broken == 'bad_hash':
            summary[field]['pis.json'] = None
        elif broken == 'wrong_type':
            summary[field] = ['pis.json']
        else:
            summary[field]['unknown-input.json'] = 'a' * 64
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(summary))
    result = G.evaluate('u', 9)
    assert result['gate'] == 'fail'
    assert any('must bind all five' in item for item in result['items'])


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1, 1.1, True, '1.0'])
def test_accuracy_cannot_pass_with_nonfinite_or_invalid_probability(tree, value):
    summary = accuracy_summary(tree)
    summary['lab_precision_uniform']['p'] = value
    (tree.root / 'acc' / 'summary-u.json').write_text(json.dumps(summary))
    result = G.evaluate('u', 9)
    assert result['gate'] == 'fail'
    assert 'finite probability' in result['items'][0]


def test_accuracy_binding_contract_matches_the_actual_drawer():
    import ast
    module = ast.parse((G.CODE / 'accuracy/sample.py').read_text())
    names = next(ast.literal_eval(node.value) for node in module.body
                 if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FILES' for t in node.targets))
    assert set(names) == set(G.ACCURACY_FILES)


def test_waiver_needs_a_reason_and_keeps_the_items(tree):
    tree.cfg['status'] = 'released'  # the legacy exception format remains valid for released schools
    tree.put('copies.json', {'summary': {'lab_papers': 10, 'local': 1}})
    tree.put('gate-exceptions.json', {'8': {'reason': '', 'by': 'owner'}})
    assert G.evaluate('u', 8)['gate'] == 'fail'
    tree.put('gate-exceptions.json', {'8': {'reason': 'owner shipped it 2026-11-02', 'by': 'owner'}})
    r = G.evaluate('u', 8)
    assert r['gate'] == 'waived' and r['open'] == 1 and r['waiver']['by'] == 'owner'


def test_onboarding_exception_requires_exact_scope_and_owner_quote(tree, monkeypatch):
    monkeypatch.setitem(G.GATES, '1', lambda key: (['CS 2016: never planned'], {}))
    tree.put('gate-exceptions.json', {'1': {'reason': 'partial coverage authorized', 'by': 'owner'}})
    r = G.evaluate('u', 1)
    assert r['gate'] == 'fail' and r['unwaived_items'] == r['items']
    assert 'allow_items' in r['exception_error']
    tree.put('gate-exceptions.json', {'1': {'reason': 'partial coverage authorized', 'allow_items': r['items']}})
    assert 'owner_quote' in G.evaluate('u', 1)['exception_error']


def test_scoped_exception_keeps_all_open_findings_visible_and_rejects_new_errors(tree, monkeypatch):
    findings = ['CS 2016: never planned']
    monkeypatch.setitem(G.GATES, '1', lambda key: (findings, {}))
    tree.put('gate-exceptions.json', {'1': {'reason': 'historical coverage incomplete', 'by': 'owner',
                                          'owner_quote': 'release what we have and keep improving',
                                          'allow_items': list(findings)}})
    r = G.evaluate('u', 1)
    assert r['gate'] == 'waived' and r['open'] == 1 and r['items'] == findings
    assert r['waived_items'] == findings and r['unwaived_items'] == []
    findings.append('evidence: source quote is missing')
    r = G.evaluate('u', 1)
    assert r['gate'] == 'fail' and r['open'] == 2
    assert r['unwaived_items'] == ['evidence: source quote is missing']
    assert r['waived_items'] == ['CS 2016: never planned']


def test_scoped_exception_does_not_match_prefixes_or_wildcards(tree, monkeypatch):
    monkeypatch.setitem(G.GATES, '5', lambda key: (['identity: missing anchor'], {}))
    tree.put('gate-exceptions.json', {'5': {'reason': 'completeness only', 'owner_quote': 'release what we have',
                                          'allow_items': ['identity:*', 'identity:']}})
    assert G.evaluate('u', 5)['gate'] == 'fail'


def test_gate10_needs_release_status_and_manifest(tree, monkeypatch):
    rel = tree.root / 'rel' / 'latest'
    rel.mkdir(parents=True)
    monkeypatch.setattr(P, 'RELEASES', tree.root / 'rel')
    import pi_states as PS
    monkeypatch.setattr(PS, 'compute', lambda key: dict(pis_total=0, open_pis=[], downloadable=0, pis={}, school_items={}, ratchet_items={}))   # per-PI part: tests/test_pi_states.py
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
    assert status == 'review' and log[1]['step'] == 'snapshot' and log[1]['result'] == 'review' and 'snapshot-ext' in log[1]['todo']   # no API sweep in stage 0
    assert not calls   # nothing local was left to run


def test_run_runs_local_steps_in_order_and_stops_on_failure(tree):
    rcs = iter([0, 3])
    seen = []

    def fake(argv, cwd=None):
        seen.append(argv[2].rsplit('/', 1)[-1])
        return SimpleNamespace(returncode=next(rcs))
    status, log = G.run_stage('u', 3, run=fake)   # census-refresh, homes (local), then the shared and lab-page steps
    assert seen[0] == 'census_build.py' and len(seen) == 2 and status == 'failed' and log[-1]['result'] == 'failed rc=3'


def test_shared_writers_need_allow_shared(tree):
    status, log = G.run_stage('u', 3, run=lambda *a, **k: SimpleNamespace(returncode=0))
    shared = [x for x in log if x['step'] == 'homes-shared']
    assert [x['step'] for x in log[:2]] == ['census-refresh', 'homes'] and shared and 'allow-shared' in shared[0]['result']


def test_dry_run_runs_nothing_and_writes_no_receipt(tree, capsys):
    G.main(['u', '2', '--run', '--dry-run'])
    assert not (tree.root / 'u' / 'reports').exists()
    assert 'dry run' in capsys.readouterr().out


def test_run_submits_the_slurm_steps_as_one_chain(tree, monkeypatch):
    import atlas_pipeline as AP
    got = {}
    monkeypatch.setattr(AP, 'submit', lambda name, schools, **k: got.update(name=name, schools=schools, **k) or {'sweep': '11'})
    tree.put('census-faculty.json', {})   # stage 2's census step already ran
    status, log = G.run_stage('u', 2, submit=True, run=lambda *a, **k: SimpleNamespace(returncode=0))
    assert status == 'submitted' and got['name'] == 'stage2-u' and got['schools'] == ['u'] and got['guard_preempt'] is True
    assert [x[0] for x in got['stages']] == ['dblp', 'sweep', 'sweepcheck', 'openalex-candidates', 'units']   # from the snapshot extension and the dump: no API sweep
    assert log[-2]['step'] == 'candidates' and log[-2]['result'] == 'waits for the queued steps'


def test_gate2_fails_until_the_candidates_file_exists(tree):
    tree.put('sweep-check.json', {'status': 'pass', 'failed': []})
    r = G.evaluate('u', 2)
    assert r['gate'] == 'fail' and 'cs-related-candidates.json missing' in r['items'][0]
    tree.put('cs-related-candidates.json', [])
    assert G.evaluate('u', 2)['gate'] == 'pass'


def test_gate5_accepts_a_reviewed_no_identity(tree, monkeypatch):
    pis = [{'name': 'Ann', 'is_pi': True}, {'name': 'Bo', 'is_pi': True, 'dblp': ['x']}]
    monkeypatch.setattr(G, 'pis_of', lambda key: pis)
    monkeypatch.setattr(G.CO, 'section', lambda key: {})
    assert G.evaluate('u', 5)['gate'] == 'fail'
    monkeypatch.setattr(G.CO, 'section', lambda key: {'Ann': {'no_identity': True, 'why_no_identity': 'searched'}})
    r = G.evaluate('u', 5)
    assert r['gate'] == 'fail' and 'identity audit missing' in r['items'][0]   # process v4: the held identity needs the seeded 50-row independent audit (tests/test_stage_audit.py)
    import stage_audit as SA
    monkeypatch.setattr(SA, 'items', lambda key, stage: ([], {}))
    r = G.evaluate('u', 5)
    assert r['gate'] == 'pass' and r['reviewed_no_identity'] == 1


def test_every_collector_stage_tool_imports_under_python_dash_I():
    """Steps run with the collector interpreter as `python -I -u`, which leaves the script's own directory off sys.path
    (UChicago PROTOCOL-FRICTION 37: labpage_students_school.py died with ModuleNotFoundError: atlas_paths). Run each with no
    arguments: it may print a usage or fail on the missing argument, never on an import."""
    import re
    import subprocess
    import sys
    from pathlib import Path
    scripts = set()
    for steps in G.STEPS.values():
        for st in steps:
            m = re.match(r'PY \$TOOLS/(\w+\.py)', st.get('cmd') or '')
            if st['kind'] == 'slurm' and st['py'] == 'collector' and m:
                scripts.add(m.group(1))
    assert scripts
    for name in sorted(scripts):
        r = subprocess.run([sys.executable, '-I', str(Path(G.__file__).with_name(name))], capture_output=True, text=True, timeout=120)
        assert 'ModuleNotFoundError' not in r.stderr and 'ImportError' not in r.stderr, (name, r.stderr[-300:])


def test_a_local_step_after_a_queued_step_waits_for_it(tree, monkeypatch):
    """Stage 1: `rows` reads the captures the queued `captures` job writes; it must not run (and fail) before them."""
    import atlas_pipeline as AP
    monkeypatch.setattr(AP, 'submit', lambda name, schools, **k: {'captures': '5'})
    calls = []
    status, log = G.run_stage('u', 1, submit=True, run=lambda argv, cwd=None: calls.append(argv) or SimpleNamespace(returncode=0))
    assert not calls and status == 'submitted'
    assert [e['result'] for e in log[:2]] == ['queued', 'waits for the queued steps']


def test_stage1_captures_are_done_when_the_plan_check_passes(tree):
    """coverage.json is written by the NEXT step (rows), so it can not prove the captures ran: the step has a check command instead."""
    st = G.STEPS['1'][0]
    assert st['name'] == 'captures' and st['check'][:1] == ['listings/scripts/plan_fetch.py']
    seen = []
    assert G.step_done('u', st, run=lambda argv, **k: seen.append(argv) or SimpleNamespace(returncode=0)) is True
    assert seen[0][-2:] == ['u', '--check'] and seen[0][1] == '-I'
    assert G.step_done('u', st, run=lambda argv, **k: SimpleNamespace(returncode=1)) is False


def test_gate3_flags_a_build_older_than_the_reviewed_inputs(tree, monkeypatch):
    """Georgia Tech friction 22: a stage-3 chain built from the census before the last stage-2 review landed."""
    import os
    monkeypatch.setattr(G, 'pis_of', lambda key: [])
    tree.put('pis.json', {})
    old = (tree.root / 'u' / 'pis.json').stat().st_mtime
    tree.put('cs-related-review.json', {})
    os.utime(tree.root / 'u' / 'cs-related-review.json', (old + 60, old + 60))
    assert any('stale build' in x for x in G.g3('u')[0])
    os.utime(tree.root / 'u' / 'cs-related-review.json', (old - 60, old - 60))
    assert not any('stale build' in x for x in G.g3('u')[0])


def test_gate3_accepts_a_bound_website_register_after_an_unchanged_pi_rebuild(tree, monkeypatch):
    import os
    import lab_websites
    monkeypatch.setattr(G, 'pis_of', lambda key: [{'name': 'Ann', 'pi_basis': {'url': 'u', 'sha256': 's', 'quote': 'q'}}])
    monkeypatch.setattr(lab_websites, 'gate', lambda *a, **kw: [])
    tree.put('pis.json', [{'pi': 'Ann'}])
    tree.put('lab-websites.json', {'pi_keys': ['Ann'], 'labs': [{'pi': 'Ann'}]})
    reg = tree.root / 'u' / 'lab-websites.json'
    pis = tree.root / 'u' / 'pis.json'
    os.utime(reg, (100, 100)); os.utime(pis, (200, 200))
    assert not any('website register' in x for x in G.g3('u')[0])
    tree.put('lab-websites.json', {'pi_keys': ['Bo'], 'labs': [{'pi': 'Bo'}]})
    assert any('website register PI keys differ' in x for x in G.g3('u')[0])


def test_a_step_is_stale_when_its_input_is_newer_than_its_output(tree):
    """R12: the stage-7 build is not done when pi-works rewrote its input after pis.json was built."""
    import os
    st = dict(name='build', kind='slurm', done=['census-faculty.json'], newer_than=['dblp-ids.json'])
    tree.put('census-faculty.json', {}); tree.put('dblp-ids.json', {})
    out, inp = tree.root / 'u' / 'census-faculty.json', tree.root / 'u' / 'dblp-ids.json'
    os.utime(out, (100, 100)); os.utime(inp, (200, 200))
    assert G.step_done('u', st) is False
    os.utime(out, (300, 300))
    assert G.step_done('u', st) is True


def test_labpage_discover_step_is_done_only_when_every_pi_has_a_record(tree):
    """R3d: the append-only discovery file exists after the first PI; a job cut short at its time limit must leave the step open."""
    import discovery_marker as DM
    step = next(s for s in G.STEPS['3'] if s['name'] == 'labpage-discover')
    tree.put('pis.json', [{'pi': 'A'}, {'pi': 'B'}, {'pi': 'C'}])
    rec = tree.root / 'u' / 'labpage-audit-discovery.jsonl'
    rec.write_text(json.dumps({'pi': 'A'}) + '\n' + json.dumps({'pi': 'B'}) + '\n{"pi": "C", "chec')   # half-written last line
    assert G.step_done('u', step) is False
    assert DM.status('u')['missing'] == ['C']
    rec.write_text(rec.read_text().split('{"pi": "C"')[0] + json.dumps({'pi': 'C'}) + '\n')
    assert G.step_done('u', step) is True
    assert DM.write_marker('u', '2026-11-17T00:00:00Z') and DM.status('u')['marker'] is True
    tree.put('pis.json', [{'pi': 'A'}, {'pi': 'B'}, {'pi': 'C'}, {'pi': 'D'}])   # a PI added after the run reopens the step
    assert G.step_done('u', step) is False and DM.status('u')['marker'] is False


def test_discovery_marker_needs_a_pis_json(tree):
    import discovery_marker as DM
    assert DM.status('u')['complete'] is False and DM.write_marker('u', 'x') is None
