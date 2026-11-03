"""tools/atlas_release.py (ROADMAP #37): the order, stop at the first failure, resume, and the confirmation for external steps."""
import json
import subprocess
from pathlib import Path

import pytest

import agent_lease
import atlas_release as AR


def go(args, runner=None):
    """AR.main in this process: --local is opt-in (the default submits a Slurm job)."""
    return AR.main(['--local', *args], runner=runner or subprocess.run)


class Runner:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, argv, env=None, stdout=None, stderr=None, cwd=None):
        stage = (env or {}).get('STAGES') or argv[1].rsplit('/', 1)[-1]
        self.calls.append(stage)
        class R:
            returncode = 1 if stage == self.fail else 0
        return R()


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k in ('STAGES', 'TAG', 'RELEASE_ARGS', 'SCHOOLS'):   # a real release runs this suite with these exported (rebuild tests stage)
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(AR.P, 'SCRATCH', tmp_path / 'scratch')
    monkeypatch.setattr(AR, 'LEASE_ROOT', tmp_path / 'leases')
    monkeypatch.setattr(AR, 'preflight', lambda c: (True, 'clean'))
    monkeypatch.setattr(AR, 'check_clean', lambda c: (True, 'clean'))
    submitted = []
    def fake_sbatch(args, env):
        submitted.append((args, env))
        return type('R', (), {'returncode': 0, 'stdout': '4242', 'stderr': ''})()
    monkeypatch.setattr(AR, 'sbatch', fake_sbatch)
    monkeypatch.setattr(AR, 'wait_jobs', lambda jobs: ('ok', {'4242_0': ('cs-build-school', 'COMPLETED', '0:0')}))
    monkeypatch.setattr(AR, 'SUBMITTED', submitted, raising=False)
    monkeypatch.setattr(AR, 'check_notes', lambda c: (True, 'notes ok'))
    monkeypatch.setattr(AR, 'handoff', lambda c: (True, 'note added'))
    pushed = []
    monkeypatch.setattr(AR, 'push_export', lambda c: pushed.append(1) or (True, 'pushed'))
    monkeypatch.setattr('sys.stdin', type('S', (), {'isatty': staticmethod(lambda: False)})())
    return pushed


def test_order_matches_the_roadmap():
    assert AR.ORDER == ['preflight', 'rebuild', 'regression', 'validate', 'reader', 'release', 'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff']


def test_stops_at_the_first_failure(env):
    r = Runner(fail='validate')
    rc = go(['--tag', 't1', '--from', 'rebuild', '--only', 'rebuild,validate,regression,reader', '--yes-push', '--yes-hf'], runner=r)
    assert rc == 1 and r.calls[-2:] == ['regression', 'validate'] and 'reader_export.py' not in r.calls    # regression runs BEFORE validate; reader never ran
    st = json.loads((AR.P.SCRATCH / 't1' / 'run.json').read_text())
    assert st['rebuild']['ok'] and st['regression']['ok'] and not st['validate']['ok'] and 'reader' not in st


def test_external_steps_need_the_flag_and_resume_skips_passed_steps(env):
    r = Runner()
    rc = go(['--tag', 't2', '--from', 'tree', '--release-id', '2026-11-02'], runner=r)
    assert rc == 3 and env == [] and r.calls == ['organize_tree.py', 'export_release.py']
    rc = go(['--tag', 't2', '--from', 'tree', '--resume', '--yes-push', '--yes-hf'], runner=r)
    assert rc == 0 and env == [1] and r.calls.count('organize_tree.py') == 1
    assert r.calls[-1].startswith('hf_upload')


def test_dry_run_lists_every_step_and_runs_nothing(env, capsys):
    r = Runner()
    assert go(['--tag', 't3', '--dry-run'], runner=r) == 0 and r.calls == []
    out = capsys.readouterr().out
    order = [ln.split()[0] for ln in out.splitlines() if ln.strip()]
    assert order == AR.ORDER
    assert 'EXTERNAL --yes-push' in out and 'EXTERNAL --yes-hf' in out


def test_handoff_note_text_has_host_link_and_take_down(tmp_path):
    d = tmp_path / 'rel'
    (d / 'reader').mkdir(parents=True)
    (d / 'MANIFEST.json').write_text(json.dumps(dict(created='2026-11-02T00:00:00Z', code=dict(commit='a' * 40), counts={'mit': dict(pis=1, lab_papers=2, students=3, student_paper_links=4)})))
    summ = dict(totals=dict(readable=5, lab_papers=9, host=2, link=3, not_readable=4), currently_hosted_not_permitted=7, link_check_request_urls=11,
                site_sync=dict(site_files=20, keep=10, unpublish=10, unpublish_by_reason={'not_in_stores': 6, 'license': 4}, upload=3))
    (d / 'reader' / 'SUMMARY.json').write_text(json.dumps(summ))
    t = AR.render_handoff('2026-11-02', d)
    assert '| mit | 1 | 2 | 3 | 4 |' in t and '## Host' in t and '## Link' in t and '## Take down (required)' in t
    assert t.index('## Host') < t.index('## Link') < t.index('## Take down')
    assert 'Remove 10 files' in t and 'not_in_stores: 6, license: 4' in t and 'reader/unpublish.tsv' in t and 'without touching our stores' in t
    assert 'Handoff for Codex' not in t and 'goes UP' not in t
    assert 'GitHub export: not performed' in t and 'Hugging Face upload: not performed' in t
    assert 'scripts/release.py prepare --release 2026-11-02' in t
    (d / 'reader' / 'SUMMARY.json').write_text(json.dumps(dict(summ, site_sync=None)))
    try:
        AR.render_handoff('2026-11-02', d)
        raise AssertionError('the note must fail without a site sync')
    except ValueError:
        pass


def test_site_target_has_no_external_steps(env, capsys):
    runner = Runner()
    assert go(['--target', 'site', '--dry-run'], runner=runner) == 0
    assert [line.split()[0] for line in capsys.readouterr().out.splitlines()] == AR.SITE_ORDER
    assert runner.calls == []


def test_unknown_step_and_implicit_resume_rejected(env):
    for args in (['--only', 'typo'], ['--only', ''], ['--tag', '../outside'], ['--resume'], ['--release-id', 'latest'], ['--from', 'notes'],
                 ['--target', 'site', '--only', 'hf-upload']):
        with pytest.raises(SystemExit) as error:
            go(args, runner=Runner())
        assert error.value.code == 2


def test_resume_binds_release_and_source_options(env):
    runner = Runner()
    assert go(['--tag', 'bound', '--from', 'tree', '--release-id', '2026-11-02'], runner=runner) == 3
    for extra in (['--release-id', '2026-11-03'], ['--schools', 'mit'], ['--target', 'site']):
        with pytest.raises(SystemExit):
            go(['--tag', 'bound', '--resume', *extra], runner=runner)
    with pytest.raises(SystemExit):
        go(['--tag', 'bound', '--from', 'tree', '--release-id', '2026-11-02'], runner=runner)


def test_freeze_receipt_retained_across_restart(env, monkeypatch, tmp_path):
    from argparse import Namespace
    context = AR.Ctx(Namespace(tag='receipt', schools=None, allow_swings=False, export_dir=None, release_id=None))
    context.dir.mkdir(parents=True)
    def freeze(argv, **kwargs):
        kwargs['stdout'].write(json.dumps({'release': '2026-11-02', 'dir': str(tmp_path / 'release')}) + '\n')
        return type('Result', (), {'returncode': 0})()
    assert AR.run_step('release', context, freeze)[0]
    assert context.release_id == '2026-11-02'
    for step in ('tree', 'export', 'hf-upload'):
        argv, _ = AR.cmd_for(step, context)
        assert '2026-11-02' in argv and 'latest' not in argv
    assert not AR.run_step('release', context, Runner())[0]


def test_resume_rechecks_preflight(env, monkeypatch):
    assert go(['--tag', 'dirty-resume', '--only', 'preflight'], runner=Runner()) == 0
    monkeypatch.setattr(AR, 'check_clean', lambda c: (False, 'uncommitted tracked changes'))
    with pytest.raises(SystemExit) as error:
        go(['--tag', 'dirty-resume', '--only', 'preflight', '--resume'], runner=Runner())
    assert error.value.code == 2


def test_regression_swings_pass_only_with_allow_swings(env):
    class Swings(Runner):
        def __call__(self, argv, env=None, stdout=None, stderr=None, cwd=None):
            stage = (env or {}).get('STAGES') or argv[1].rsplit('/', 1)[-1]
            self.calls.append(stage)
            class R:
                returncode = 2 if stage == 'regression' else 0
            return R()
    assert go(['--tag', 's1', '--from', 'regression', '--only', 'regression'], runner=Swings()) == 1
    assert go(['--tag', 's2', '--from', 'regression', '--only', 'regression', '--allow-swings'], runner=Swings()) == 0
    st = json.loads((AR.P.SCRATCH / 's2' / 'run.json').read_text())
    assert st['regression']['ok'] and 'swings allowed' in st['regression']['message']


# ---- 2026-11-03: the fast, fail-early release ----

REBUILD_SH = Path(AR.__file__).resolve().parents[1] / 'hierarchy' / 'rebuild.sh'


def test_regression_runs_before_validate_and_zero_paper_follows_the_build():
    assert AR.ORDER.index('regression') < AR.ORDER.index('validate')
    st = AR.REBUILD_STAGES
    assert st.index('build') < st.index('zero_paper') < st.index('ids')


def test_rebuild_sh_stage_list_matches_the_release(tmp_path):
    text = REBUILD_SH.read_text()
    default = next(ln for ln in text.splitlines() if ln.startswith('STAGES=${STAGES:-')).split(':-', 1)[1].rstrip('}').split()
    known = next(ln for ln in text.splitlines() if ln.startswith('KNOWN_STAGES=')).split('"')[1].split()
    assert default == [x for x in known]                                         # one list, one order
    assert [x for x in default if x in AR.REBUILD_STAGES] == AR.REBUILD_STAGES   # the release runs them in rebuild.sh's order
    assert default.index('regression') < default.index('validate') and default.index('build') < default.index('zero_paper')


def rebuild_sh(*args):
    return subprocess.run(['bash', str(REBUILD_SH), *args], capture_output=True, text=True, timeout=60,
                          env={k: v for k, v in __import__('os').environ.items() if k not in ('STAGES', 'TAG', 'SCHOOLS', 'BEFORE')})


def test_rebuild_sh_takes_stages_as_an_argument_and_refuses_the_rest():
    r = rebuild_sh('STAGES=tests', 'SCHOOLS=mit', '--list')
    assert r.returncode == 0 and 'stages: tests' in r.stdout and 'schools: mit' in r.stdout     # the argument is honoured, not ignored
    for bad in (['tests'], ['--stages=tests'], ['STAGES=bogus'], ['STAGES=tests nope'], ['FOO=1']):
        r = rebuild_sh(*bad, '--list')
        assert r.returncode == 2 and 'rebuild.sh:' in r.stderr and 'stages:' not in r.stdout, bad


def test_build_is_a_per_school_array_newest_school_first(env):
    r = Runner()
    assert go(['--tag', 'arr', '--only', 'rebuild'], runner=r) == 0
    assert 'build' not in r.calls and r.calls == [x for x in AR.REBUILD_STAGES if x != 'build']
    test_only, real = AR.SUBMITTED
    assert '--test-only' in test_only[0] and '--test-only' not in real[0]            # --test-only first
    schools = list(AR.P.SCHOOL_IDS)
    assert real[1]['SCHOOL_LIST'].split() == schools[::-1] and real[1]['MODE'] == 'build'
    assert f'--array=0-{len(schools) - 1}' in real[0]


def test_serial_build_runs_the_stage_in_the_job(env):
    r = Runner()
    assert go(['--tag', 'ser', '--only', 'rebuild', '--serial-build'], runner=r) == 0
    assert r.calls == AR.REBUILD_STAGES and AR.SUBMITTED == []


def test_build_array_is_not_submitted_on_preempts(env, monkeypatch):
    monkeypatch.setattr(AR, 'sbatch', lambda args, e: type('R', (), {'returncode': 0, 'stdout': '', 'stderr': 'Preempts: 99'})())
    assert go(['--tag', 'pre', '--only', 'rebuild'], runner=Runner()) == 1
    st = json.loads((AR.P.SCRATCH / 'pre' / 'run.json').read_text())
    assert not st['rebuild_stages']['build']['ok'] and 'Preempts' in st['rebuild_stages']['build']['message']


def test_resume_restarts_at_the_failed_stage(env):
    assert go(['--tag', 'rs', '--only', 'rebuild', '--serial-build'], runner=Runner(fail='ids')) == 1
    st = json.loads((AR.P.SCRATCH / 'rs' / 'run.json').read_text())
    assert [k for k, v in st['rebuild_stages'].items() if v['ok']] == ['snapshot', 'build', 'zero_paper'] and not st['rebuild_stages']['ids']['ok']
    r = Runner()
    assert go(['--tag', 'rs', '--only', 'rebuild', '--serial-build', '--resume'], runner=r) == 0
    assert r.calls == AR.REBUILD_STAGES[AR.REBUILD_STAGES.index('ids'):]            # no snapshot, build or zero_paper again


@pytest.fixture
def two_commits(env, monkeypatch):
    real = AR.git
    changed = []
    def fake(*a, cwd=None):
        if a[0] == 'diff':
            return type('R', (), {'returncode': 0, 'stdout': '\n'.join(changed), 'stderr': ''})()
        return real(*a, cwd=cwd)
    monkeypatch.setattr(AR, 'git', fake)
    monkeypatch.setenv('CS_ATLAS_SNAPSHOT_COMMIT', 'a' * 40)
    assert go(['--tag', 'cc', '--only', 'rebuild', '--serial-build'], runner=Runner(fail='audits')) == 1
    monkeypatch.setenv('CS_ATLAS_SNAPSHOT_COMMIT', 'b' * 40)
    return changed


def test_resume_across_a_docs_only_commit_is_allowed_with_a_note(two_commits, capsys):
    two_commits[:] = ['docs/RUNBOOK.md', 'docs/ROADMAP.md']
    r = Runner()
    assert go(['--tag', 'cc', '--only', 'rebuild', '--serial-build', '--resume'], runner=r) == 0
    assert r.calls == ['audits', 'evidence', 'tests'] and 'NOTE: resuming across commits aaaaaaaaaa -> bbbbbbbbbb' in capsys.readouterr().out
    assert 'only tests/ and docs/ changed' in json.loads((AR.P.SCRATCH / 'cc' / 'run.json').read_text())['_notes'][0]


def test_resume_across_a_commit_touching_tests_reruns_the_tests_stage(two_commits):
    two_commits[:] = ['tests/test_x.py']
    r = Runner()
    assert go(['--tag', 'cc', '--only', 'rebuild', '--serial-build', '--resume'], runner=r) == 0
    assert r.calls == ['audits', 'evidence', 'tests']


def test_resume_across_a_code_commit_is_refused(two_commits, capsys):
    two_commits[:] = ['docs/RUNBOOK.md', 'tools/make_release.py']
    with pytest.raises(SystemExit) as error:
        go(['--tag', 'cc', '--only', 'rebuild', '--serial-build', '--resume'], runner=Runner())
    assert error.value.code == 2 and 'tools/make_release.py' in capsys.readouterr().err


def test_second_release_is_refused_while_the_lock_is_held(env, capsys):
    ok, _ = agent_lease.acquire(AR.LOCK_NAME, session='release:otherhost:1', ttl=600, note='release-77 job 77', root=AR.LEASE_ROOT)
    assert ok
    r = Runner()
    assert go(['--tag', 'lk', '--only', 'preflight'], runner=r) == 1
    err = capsys.readouterr().err
    assert 'another release is running' in err and 'release-77 job 77' in err and 'release:otherhost:1' in err
    assert r.calls == [] and not (AR.P.SCRATCH / 'lk' / 'run.json').exists()
    assert AR.submit_and_wait(['--tag', 'x'], run=lambda *a, **k: (_ for _ in ()).throw(AssertionError('sbatch must not be called'))) == 1


def test_lock_is_taken_and_released_on_exit_also_after_a_failure(env):
    seen = []
    class Spy(Runner):
        def __call__(self, argv, **kw):
            holder = AR.lock_holder(AR.LEASE_ROOT)
            seen.append(holder and holder['host'])
            return super().__call__(argv, **kw)
    assert go(['--tag', 'lk2', '--only', 'validate'], runner=Spy(fail='validate')) == 1
    assert seen and seen[0] and AR.lock_holder(AR.LEASE_ROOT) is None              # held during the run (with its host), free after the failure
    assert go(['--tag', 'lk3', '--only', 'validate'], runner=Spy()) == 0 and AR.lock_holder(AR.LEASE_ROOT) is None


def test_expired_lock_does_not_block(env):
    agent_lease.acquire(AR.LOCK_NAME, session='release:gone:1', ttl=-10, root=AR.LEASE_ROOT)
    assert go(['--tag', 'lk4', '--only', 'validate'], runner=Runner()) == 0


def test_default_submits_a_slurm_job_and_local_is_opt_in(env, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(AR, 'submit_and_wait', lambda args, **k: calls.append(args) or 0)
    assert AR.main(['--tag', 'sl', '--wait']) == 0 and calls == [['--tag', 'sl']]          # --wait is accepted, the default
    assert AR.main(['--tag', 'sl2', '--allow-swings']) == 0 and calls[1] == ['--tag', 'sl2', '--allow-swings']
    runner = Runner()
    assert AR.main(['--local', '--tag', 'sl3', '--only', 'validate'], runner=runner) == 0 and runner.calls == ['validate'] and len(calls) == 2
    assert AR.main(['--dry-run'], runner=runner) == 0 and len(calls) == 2                  # a dry run submits nothing
    slurm = (Path(AR.__file__).resolve().parents[1] / 'hierarchy' / 'release.slurm').read_text()
    assert 'atlas_release.py" --local' in slurm                                          # the job itself runs locally, as the job


def test_submit_and_wait_checks_test_only_first_and_passes_the_args(env):
    seen = []
    def run(argv, **kw):
        seen.append(argv)
        return type('R', (), {'returncode': 0, 'stdout': '9;x\n' if argv[0] == 'sbatch' and '--test-only' not in argv else 'abc\n', 'stderr': ''})()
    rc = AR.submit_and_wait(['--tag', 't', '--swings-file', '/x y'], run=run, wait=lambda jobs, run=None: ('ok', {}))
    sb = [a for a in seen if a[0] == 'sbatch']
    assert rc == 0 and '--test-only' in sb[0] and '--test-only' not in sb[1]


@pytest.fixture
def pf(env, monkeypatch, tmp_path):
    """The real preflight with git, the last release and the runner faked."""
    monkeypatch.undo()
    for k in ('STAGES', 'TAG', 'RELEASE_ARGS', 'SCHOOLS'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(AR.P, 'SCRATCH', tmp_path / 'scratch')
    monkeypatch.setattr(AR, 'LEASE_ROOT', tmp_path / 'leases')
    real = AR.git
    def fake(*a, cwd=None):
        if a[:2] == ('rev-parse', '--abbrev-ref'):
            return type('R', (), {'returncode': 0, 'stdout': 'main\n', 'stderr': ''})()
        if a[0] == 'status':
            return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        return real(*a, cwd=cwd)
    monkeypatch.setattr(AR, 'git', fake)
    rel = tmp_path / 'rel' / 'hierarchy'
    rel.mkdir(parents=True)
    monkeypatch.setattr(AR, 'last_release_hierarchy', lambda: rel)
    monkeypatch.setattr(AR, 'sbatch', lambda args, e: type('R', (), {'returncode': 0, 'stdout': '1', 'stderr': ''})())
    return tmp_path


class PfRunner:
    def __init__(self, fail=(), flags=()):
        self.calls, self.fail, self.flags = [], set(fail), list(flags)

    def __call__(self, argv, env=None, stdout=None, stderr=None, cwd=None):
        name = argv[1].rsplit('/', 1)[-1] if argv[0] != 'bash' else 'rebuild.sh'
        sub = argv[2] if len(argv) > 2 else ''
        self.calls.append((name, sub, dict(env or {})))
        rc = 1 if name.split('.')[0] in self.fail or (name == 'rebuild.sh' and 'tests' in self.fail) else 0
        if name == 'build_regression.py' and sub == 'check':
            Path(argv[argv.index('--json') + 1]).write_text(json.dumps(dict(flags=self.flags)))
            rc = 2 if self.flags else 0
        if rc and stdout:
            stdout.write(f'FAILED {name}\n')
        return type('R', (), {'returncode': rc})()


def preflight_args(extra=()):
    return ['--local', '--tag', 'pfx', '--preflight-only', *extra]


def test_preflight_runs_every_check_with_the_releases_own_environment(pf):
    r = PfRunner()
    assert AR.main(preflight_args(), runner=r) == 0
    names = [c[0] for c in r.calls]
    assert {'rebuild.sh', 'validate.py', 'evidence_check.py', 'build_regression.py'} <= set(names)
    tests = next(c for c in r.calls if c[0] == 'rebuild.sh')
    assert tests[2]['STAGES'] == 'tests' and tests[2]['TAG'] == 'pfx' and '--preflight-only' in tests[2]['RELEASE_ARGS'] and tests[2]['CS_ATLAS_SNAPSHOT_COMMIT']   # (b)
    assert not any(n in ('pi_hierarchy.py', 'make_release.py') for n in names)             # nothing is built or frozen
    pj = json.loads((AR.P.SCRATCH / 'pfx' / 'preflight.json').read_text())
    assert pj['ok'] and pj['seconds'] >= 0


def test_preflight_reports_every_failure_at_once(pf):
    r = PfRunner(fail={'tests', 'validate', 'evidence_check'})
    assert AR.main(preflight_args(), runner=r) == 1
    msg = json.loads((AR.P.SCRATCH / 'pfx' / 'run.json').read_text())['preflight']['message']
    assert 'tests: failed' in msg and 'validate: failed' in msg and 'evidence: failed' in msg and 'FAILED' in msg


def test_preflight_lists_swings_and_needs_a_signoff(pf, capsys):
    flags = [dict(school='mit', kind='school_count', count='lab_papers', before=10, after=30), dict(school='cmu', kind='pi_loss', pi='A B', before=50, after=1)]
    assert AR.main(preflight_args(), runner=PfRunner(flags=flags)) == 1
    out = capsys.readouterr().out
    assert 'swing school_count|mit|lab_papers' in out and 'swing pi_loss|cmu|A B' in out and '2 regression swing(s)' in out
    assert AR.main(['--local', '--tag', 'pfy', '--preflight-only', '--allow-swings'], runner=PfRunner(flags=flags)) == 0
    sign = pf / 'swings.json'
    sign.write_text(json.dumps(dict(signed_by='owner', signed_at='2026-11-03', swings=['school_count|mit|lab_papers'])))
    assert AR.main(['--local', '--tag', 'pfz', '--preflight-only', '--swings-file', str(sign)], runner=PfRunner(flags=flags)) == 1     # one swing still unsigned
    sign.write_text(json.dumps(dict(signed_by='owner', signed_at='2026-11-03', swings=[AR.swing_id(f) for f in flags])))
    assert AR.main(['--local', '--tag', 'pfw', '--preflight-only', '--swings-file', str(sign)], runner=PfRunner(flags=flags)) == 0


def test_unsigned_swings_file_does_not_approve(pf):
    f = pf / 'swings.json'
    f.write_text(json.dumps(dict(swings=['x'])))
    ok, ids, missing, err = AR.swings_verdict([dict(kind='k', school='s')], False, str(f))
    assert not ok and 'not signed' in err
    assert AR.swings_verdict([], False, None)[0] and AR.swings_verdict([dict(kind='k')], True, None)[0]


def test_preflight_fails_on_a_dirty_main_checkout_without_stopping_the_other_checks(pf, monkeypatch):
    real = AR.git
    monkeypatch.setattr(AR, 'git', lambda *a, cwd=None: type('R', (), {'returncode': 0, 'stdout': ' M tools/x.py\n' if a[0] == 'status' else 'main\n', 'stderr': ''})()
                        if a[0] in ('status', 'rev-parse') and a[:2] != ('rev-parse', 'HEAD') else real(*a, cwd=cwd))
    r = PfRunner(fail={'validate'})
    assert AR.main(preflight_args(), runner=r) == 1
    msg = json.loads((AR.P.SCRATCH / 'pfx' / 'run.json').read_text())['preflight']['message']
    assert 'uncommitted tracked changes' in msg and 'validate: failed' in msg


def test_regression_step_accepts_signed_swings_and_the_release_freeze_follows(env, monkeypatch, tmp_path):
    flags = [dict(school='mit', kind='school_count', count='lab_papers')]
    monkeypatch.setattr(AR.P, 'data', lambda name, *a: tmp_path / name)
    (tmp_path / 'BUILD-REGRESSION.json').write_text(json.dumps(dict(flags=flags)))
    class Swings(Runner):
        def __call__(self, argv, env=None, **kw):
            super().__call__(argv, env=env, **kw)
            return type('R', (), {'returncode': 2 if (env or {}).get('STAGES') == 'regression' else 0})()
    sign = tmp_path / 'ok.json'
    sign.write_text(json.dumps(dict(signed_by='o', signed_at='2026-11-03', swings=[AR.swing_id(flags[0])])))
    assert go(['--tag', 'sg', '--from', 'regression', '--only', 'regression,release', '--swings-file', str(sign)], runner=Swings()) == 1   # release has no receipt here
    st = json.loads((AR.P.SCRATCH / 'sg' / 'run.json').read_text())
    assert st['regression']['ok'] and 'approved by the signed swings file' in st['regression']['message'] and st['_swings_approved']
    from argparse import Namespace
    c = AR.Ctx(Namespace(tag='sg', schools=None, allow_swings=False, export_dir=None, release_id=None))
    c.state = st
    assert '--allow-swings' in AR.cmd_for('release', c)[0]
    sign.write_text(json.dumps(dict(signed_by='o', signed_at='2026-11-03', swings=['other'])))
    assert go(['--tag', 'sg2', '--only', 'regression', '--swings-file', str(sign)], runner=Swings()) == 1


def test_dry_run_shows_the_rebuild_stages_and_build_mode(env, capsys):
    assert go(['--tag', 'dr', '--dry-run'], runner=Runner()) == 0
    line = next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith('rebuild'))
    assert 'zero_paper' in line and 'build[array, newest first]' in line
