"""tools/onboarding_traps.py: each known onboarding trap is a check that fires on the failure and stays quiet on the fixed state."""
import json
import subprocess

import onboarding_traps as T
import school_config as S


def put(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))
    return p


def test_collector_without_loop_job_or_signal_is_found(tmp_path):
    d = tmp_path / 'fulltext-push'
    d.mkdir()
    (d / 'x-collector.slurm').write_text('#!/bin/bash\n#SBATCH --time=1\n./run.sh\n')
    (d / 'ok-collector.slurm').write_text('#SBATCH --signal=B:USR1@900\n. fulltext-push/loop_job.sh\n')
    f = T.collector_traps(tmp_path)
    assert len(f) == 2 and all('x-collector.slurm' in x for x in f)


def test_every_collector_script_of_the_repository_restarts_itself():
    assert T.collector_traps() == []   # a new collector script that forgets loop_job fails here, before it ends at its limit and stays down


def test_charter_traps_name_the_missing_later_stage_configs(monkeypatch):
    cfg = dict(status='onboarding', affiliation=dict(regex='x'), dblp={}, repository={}, thesis={})
    monkeypatch.setattr(S, 'get', lambda k: cfg)
    f = ' '.join(T.charter_traps('newu'))
    for w in ('must_match', 'loose', 'affiliation_strings', 'repository].name', 'repository].pattern', 'thesis].kind'):
        assert w in f
    cfg.update(affiliation=dict(regex='x', loose='x', must_match=['x'], must_not_match=['y']), dblp=dict(affiliation_strings=['x']),
               repository=dict(name='R', pattern='r\\.edu'), thesis=dict(kind='none'))
    assert T.charter_traps('newu') == []
    cfg['repository']['pattern'] = '('
    assert 'does not compile' in T.charter_traps('newu')[0]
    cfg['status'] = 'released'
    assert T.charter_traps('newu') == []


def test_missing_capture_store(tmp_path, monkeypatch):
    import atlas_paths as P
    monkeypatch.setattr(T.P, 'data', lambda name, key=None, **k: tmp_path / name)
    assert 'neither' in T.captures_traps('newu')[0]
    (tmp_path / 'labpage-audit-captures.sqlite').write_text('')   # the audit store alone is enough
    assert T.captures_traps('newu') == []
    assert P  # imported for the monkeypatch target


def test_shared_file_section_of_an_onboarding_school(tmp_path, monkeypatch):
    monkeypatch.setattr(S, 'get', lambda k: dict(status='onboarding'))
    shared = put(tmp_path / 'census-overrides.json', {'_note': 'x', 'mit': {}, 'newu': {'a': 1}})
    f = T.shared_traps('newu', files={'census-overrides.json': shared, 'labpage-audit-summary.json': tmp_path / 'none', 'student-audit.json': tmp_path / 'none'})
    assert len(f) == 1 and 'census-overrides-school.json' in f[0]
    shared.write_text(json.dumps({'mit': {}}))
    assert T.shared_traps('newu', files={'census-overrides.json': shared, 'labpage-audit-summary.json': tmp_path / 'none', 'student-audit.json': tmp_path / 'none'}) == []
    monkeypatch.setattr(S, 'get', lambda k: dict(status='released'))
    put(shared, {'newu': {}})
    assert T.shared_traps('newu', files={'census-overrides.json': shared}) == []


def test_ignored_reviewed_file_is_found(tmp_path):
    repo = tmp_path / 'r'
    (repo / 'hierarchy' / 'newu' / 'reviewed').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo / '.gitignore').write_text('hierarchy/*/reviewed/*\n!hierarchy/*/reviewed/ok.json\n')
    rd = repo / 'hierarchy' / 'newu' / 'reviewed'
    (rd / 'ok.json').write_text('{}')
    (rd / 'lost.json').write_text('{}')
    f = T.ignored_traps('newu', repo=repo, reviewed=rd)
    assert len(f) == 1 and 'lost.json' in f[0]


def test_additions_shrunk_below_the_acceptance(tmp_path):
    acc = put(tmp_path / 'acc.json', dict(students=dict(accepted=True, counts=dict(proposed=3)), papers=dict(accepted=True, counts=dict(proposed=2))))
    add = put(tmp_path / 'add.json', dict(students=[], papers=[1, 2]))
    f = T.additions_traps('newu', additions=add, acceptance=acc)
    assert len(f) == 1 and 'holds 0 students' in f[0] and 'accepted 3' in f[0]
    put(add, dict(students=[1, 2, 3], papers=[1, 2]))
    assert T.additions_traps('newu', additions=add, acceptance=acc) == []


def test_stale_recorded_gate_file(tmp_path):
    import os
    rep = tmp_path / 'reports'
    g = put(rep / 'stage-6-gate.json', {})
    inp = put(tmp_path / 'labpage-acceptance.json', {})
    os.utime(g, (1000, 1000))
    os.utime(inp, (2000, 2000))
    f = T.stale_traps('newu', reports=rep, inputs={'labpage-acceptance.json': inp, 'labpage-additions.json': tmp_path / 'no', 'student-decisions.json': tmp_path / 'no'})
    assert len(f) == 1 and 'stage-6-gate.json' in f[0]
    os.utime(g, (3000, 3000))
    assert T.stale_traps('newu', reports=rep, inputs={'labpage-acceptance.json': inp}) == []


def test_stage_gate_adds_the_traps_of_its_stage(monkeypatch):
    import stage_gate as G
    monkeypatch.setitem(G.GATES, '0', lambda key: ([], {}))
    monkeypatch.setattr(T, 'for_stage', lambda key, stage: ['charter: x'] if int(stage) == 0 else [])
    r = G.evaluate('newu', 0)
    assert r['gate'] == 'fail' and r['items'] == ['charter: x']
    monkeypatch.setitem(G.GATES, '1', lambda key: ([], {}))
    assert G.evaluate('newu', 1)['gate'] == 'pass'


def test_ledger_reads_the_repository_from_the_charter(monkeypatch):
    import unavailable_ledger as U
    cfg = dict(repository=dict(name='Repo X', pattern='repo\\.x\\.edu'))
    monkeypatch.setattr(S, 'get', lambda k: cfg)
    assert U.repo_name('newu') == 'Repo X' and U.repo_pattern('newu') == 'repo\\.x\\.edu'
    assert U.repo_name('gatech').startswith('the Georgia Tech repository')   # the tables still win for the existing schools
    cfg['repository'] = {}
    import pytest
    with pytest.raises(KeyError):
        U.repo_pattern('newu')


def test_regenerated_evidence_is_not_an_ignored_finding(tmp_path):
    repo = tmp_path / 'r'
    rd = repo / 'hierarchy' / 'newu' / 'reviewed'
    rd.mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo / '.gitignore').write_text('hierarchy/*/reviewed/*\n')
    (rd / 'labpage-evidence.json').write_text('{}')   # regenerated from raw captures: ignored on purpose
    assert T.ignored_traps('newu', repo=repo, reviewed=rd) == []


def test_record_writes_the_gate_file_without_running_steps(tmp_path, monkeypatch):
    import stage_gate as G
    monkeypatch.setattr(G.P, 'HIERARCHY', tmp_path)
    monkeypatch.setitem(G.GATES, '1', lambda key: ([], dict(n=1)))
    monkeypatch.setattr(G, 'traps_for', lambda key, stage: [])
    assert G.main(['newu', '1', '--record']) == 0
    rec = json.loads((tmp_path / 'newu' / 'reports' / 'stage-1-gate.json').read_text())
    assert rec['result']['gate'] == 'pass' and rec['run'] is None


def test_copy_share_below_the_target_is_reported_not_failed(tmp_path, monkeypatch):
    import stage_gate as G
    files = {'copies.json': dict(summary=dict(lab_papers=100, local=42)), 'unavailable-summary.json': {'n': 58}}
    monkeypatch.setattr(G, 'read', lambda p, default=None: files.get(__import__('pathlib').Path(p).name, default))
    monkeypatch.setattr(G.P, 'data', lambda name, key=None, **k: tmp_path / name)
    bad, n = G.g8('newu')
    assert bad == [] and n['copy_target_met'] is False and n['local_share'] == 0.42
    files.pop('unavailable-summary.json')
    assert 'ledger' in G.g8('newu')[0][0]   # an unexplained shortfall still fails


def test_boilerplate_sources_exhausted_reasons_are_a_finding(tmp_path):
    def entry(why, n):
        return dict(students=dict(code='sources_exhausted', why=why, sources_checked=['a'] * n))
    rs = {f'P{i}': entry(T.BOILERPLATE + ' (Professor).', 3) for i in range(6)}
    rs['Q'] = entry('Searched CV and group page.', 1)
    f = T.reasons_traps('newu', reasons=put(tmp_path / 'r.json', rs), n_pis=10)
    assert any('fewer than 2' in x for x in f) and any('6 of 10' in x for x in f)
    ok = {f'P{i}': entry(T.BOILERPLATE + '.', 3) for i in range(2)}
    assert T.reasons_traps('newu', reasons=put(tmp_path / 'r.json', ok), n_pis=10) == []


def test_traps_flag_is_stage_scoped_so_stage_zero_can_pass(monkeypatch):
    assert set(T.CHECK_FROM) == set(T.CHECKS)                       # every check declares its first stage
    assert 'captures' not in T.checks_upto(0) and 'captures' not in T.checks_upto(2) and 'captures' in T.checks_upto(3)
    assert 'additions' not in T.checks_upto(5) and set(T.checks_upto()) == set(T.CHECKS)
    import stage_gate as G
    seen = []
    monkeypatch.setattr(T, 'run', lambda key, names: (seen.append(list(names)), [])[1])
    assert G.main(['newu', '0', '--traps']) == 0 and 'captures' not in seen[0] and 'charter' in seen[0]
    G.main(['newu', '--traps'])
    assert 'captures' in seen[1]
