"""tools/atlas_pipeline.py (ROADMAP #34): every stage is chained afterok to the one before, per-school stages are arrays, the command travels safely."""
import atlas_pipeline as AP


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, capture_output=None, text=None, env=None, cwd=None):
        self.calls.append((argv, env))
        n = len(self.calls)

        class R:
            returncode, stdout, stderr = 0, f'{1000 + n}', ''
        return R()


def test_stages_chain_with_afterok_and_arrays_per_school():
    run = FakeRun()
    jobs = AP.submit('copies', ['mit', 'cmu'], run=run, commit='a' * 40)
    assert list(jobs) == ['copies', 'ledger', 'recount', 'status'] and list(jobs.values()) == ['1001', '1002', '1003', '1004']
    first, second = run.calls[0][0], run.calls[1][0]
    assert '--array=0-1' in first and not any(x.startswith('--dependency') for x in first)
    assert '--dependency=afterok:1001' in second and not any(x.startswith('--array') for x in second)
    assert run.calls[3][0].count('--dependency=afterok:1003') == 1
    env = run.calls[1][1]
    assert env['PIPE_CMD'].startswith('PY $FTP/unavailable_ledger.py') and env['CS_ATLAS_SNAPSHOT_COMMIT'] == 'a' * 40
    assert '--export=ALL' in second and env['PIPE_STAGE'] == 'ledger' and env['PIPE_PY'] == 'collector' and env['SCHOOL_LIST'] == 'mit cmu'


def test_test_only_checks_the_first_stage_only():
    run = FakeRun()
    assert AP.submit('labpage', ['mit'], run=run, test_only=True, commit='b' * 40) == {} and len(run.calls) == 1 and '--test-only' in run.calls[0][0]


def test_registry_is_well_formed():
    for name, stages in AP.PIPELINES.items():
        assert len({s[0] for s in stages}) == len(stages), name
        for stage, kind, cmd, py, cpus, mem, tm in stages:
            assert (kind in ('school', 'once') or kind.startswith('array:')) and py in ('project', 'collector') and cmd.startswith('PY ')
            assert ('{school}' in cmd) == (kind == 'school' or kind.startswith('array:')), (name, stage)


def test_onboard_data_chain_and_a_worktree_snapshot_repo(tmp_path):
    run = FakeRun()
    jobs = AP.submit('onboard-data', ['newu'], run=run, commit='c' * 40, repo=tmp_path)
    assert list(jobs) == ['dblp', 'sweep', 'sweepcheck', 'candidates'] and all('--array=0-0' in c[0] for c in run.calls)
    assert run.calls[1][1]['SNAPSHOT_REPO'] == str(tmp_path) and run.calls[1][1]['PIPE_CMD'] == 'PY $TOOLS/sweep_from_snapshot.py newu --replace'.replace('newu', '{school}')


def test_snapshot_ext_is_a_16_task_array_then_a_merge_and_status_shows_dependencies():
    run = FakeRun()
    jobs = AP.submit('snapshot-ext', ['newu'], run=run, commit='d' * 40)
    assert list(jobs) == ['filter', 'merge'] and '--array=0-15' in run.calls[0][0] and run.calls[0][1]['PIPE_KIND'] == 'array:16'
    assert '--dependency=afterok:1001' in run.calls[1][0] and '--ext {schools}' in run.calls[1][1]['PIPE_CMD']
    assert '{task}' in run.calls[0][1]['PIPE_CMD'] and '--array' not in ' '.join(run.calls[1][0])

    def squeue(argv, capture_output=None, text=None):
        class R:
            returncode, stdout, stderr = 0, '32079156 PENDING dependency=afterany:32079275(unfulfilled)\n', ''
        assert argv[0] == 'squeue'
        return R()
    assert 'dependency=afterany:32079275' in AP.dependency_lines(['32079156'], squeue)


def test_only_runs_the_named_stage(monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(AP, 'submit', lambda name, schools, **k: (run.calls.append(k), {'candidates': '1'})[1])
    monkeypatch.setattr(AP.P, 'SCRATCH', '/tmp')
    monkeypatch.setattr(AP.Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(AP.Path, 'write_text', lambda *a, **k: 0)
    AP.main(['onboard-data', 'SCHOOLS=newu', '--only', 'candidates'], run=run)
    assert [st[0] for st in run.calls[0]['stages']] == ['candidates']


def argv_of(run, i=0):
    return run.calls[i][0]


def test_stages_follow_the_standing_slurm_rules(monkeypatch):
    for k in ('SBATCH_PARTITION', 'SBATCH_ACCOUNT', 'SBATCH_EXCLUDE', 'SBATCH_TIMELIMIT'):
        monkeypatch.delenv(k, raising=False)
    run = FakeRun()
    AP.submit('snapshot-ext', ['newu'], run=run, commit='e' * 40)
    for i in (0, 1):
        a = argv_of(run, i)
        assert '--partition=all' in a and '--account=mltheory' in a and '--exclude=node302,node014' in a and '--time=00:59:00' in a, a
    assert AP.long_stages('snapshot-ext') == []


def test_sbatch_variables_override_the_defaults(monkeypatch):
    monkeypatch.setenv('SBATCH_PARTITION', 'lowprio'); monkeypatch.setenv('SBATCH_EXCLUDE', 'node302'); monkeypatch.setenv('SBATCH_TIMELIMIT', '01:30:00')
    run = FakeRun()
    AP.submit('snapshot-ext', ['newu'], run=run, commit='e' * 40)
    a = argv_of(run)
    assert '--partition=lowprio' in a and '--exclude=node302' in a and '--time=01:30:00' in a and '--account=mltheory' in a
    assert [s for s, _ in AP.long_stages('snapshot-ext')] == ['filter', 'merge']


def test_every_chain_gets_the_node_and_partition_rules_and_long_stages_are_named(monkeypatch):
    monkeypatch.delenv('SBATCH_TIMELIMIT', raising=False)
    for name in AP.PIPELINES:
        for stage, args, env, cmd in AP.plan(name, ['newu']):
            assert {'--partition=all', '--account=mltheory', '--exclude=node302,node014'} <= set(args), (name, stage)
    assert ('audit', '12:00:00') in AP.long_stages('labpage')
    assert AP.minutes('00:59:00') == 59 and AP.minutes('1-00:00:00') == 1440 and AP.minutes('30') == 30


def test_flags_set_the_sbatch_variables(monkeypatch):
    for k in ('SBATCH_PARTITION', 'SBATCH_ACCOUNT', 'SBATCH_EXCLUDE', 'SBATCH_TIMELIMIT'):
        monkeypatch.setenv(k, '')   # registers the restore; empty means "use the default"
    run = FakeRun()
    monkeypatch.setattr(AP.P, 'SCRATCH', '/tmp')
    monkeypatch.setattr(AP.Path, 'mkdir', lambda *a, **k: None)
    monkeypatch.setattr(AP.Path, 'write_text', lambda *a, **k: 0)
    monkeypatch.setattr(AP.subprocess, 'run', lambda *a, **k: type('R', (), dict(stdout='x' * 40, stderr='', returncode=0))())
    AP.main(['snapshot-ext', 'SCHOOLS=newu', 'OA_DATE=2026-10-14', 'SBATCH_EXCLUDE=node1', '--time', '00:40:00', '--partition', 'lowprio'], run=run)
    probe = run.calls[0][0]
    assert '--time=00:40:00' in probe and '--partition=lowprio' in probe and '--exclude=node1' in probe and '--test-only' in probe


def test_snapshot_cli_date_reaches_probe_filter_and_merge(monkeypatch, tmp_path):
    run = FakeRun()
    monkeypatch.setattr(AP.P, 'SCRATCH', tmp_path)
    monkeypatch.setattr(AP.subprocess, 'run', lambda *a, **k: type('R', (), dict(stdout='f' * 40, stderr='', returncode=0))())
    AP.main(['snapshot-ext', 'SCHOOLS=newu', 'OA_DATE=2026-10-14'], run=run)
    assert len(run.calls) == 3
    assert all(env['OA_DATE'] == '2026-10-14' for _, env in run.calls)
    assert all('%A_%a.out' in next(x for x in args if x.startswith('--output=')) for args, _ in run.calls[:2])
    assert '%A.out' in next(x for x in run.calls[2][0] if x.startswith('--output='))
