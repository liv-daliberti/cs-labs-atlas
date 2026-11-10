"""tools/agent_worktree.sh land: the test gate runs through srun (stub on PATH), keeps the test exit code, and never lands unverified."""
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'tools' / 'agent_worktree.sh'
GIT = ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.org']


def _git(cwd, *a):
    return subprocess.run([*GIT, *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _fixture(tmp_path):
    """tmp/code (main) + tmp/worktrees/w on agent/w with one commit ahead; stub bin/atlas; stub srun dir."""
    main = tmp_path / 'code'
    (main / 'tools').mkdir(parents=True)
    (main / 'bin').mkdir()
    shutil.copy(SCRIPT, main / 'tools' / 'agent_worktree.sh')
    (main / 'bin' / 'atlas').write_text(textwrap.dedent('''\
        #!/bin/bash
        case "$1" in
          test) echo "stub tests run on $(hostname)"; exit "${STUB_TEST_RC:-0}" ;;
          task) echo ours; exit 0 ;;
          *) exit 0 ;;
        esac
        '''))
    (main / 'bin' / 'atlas').chmod(0o755)
    _git(main, 'init', '-q', '-b', 'main')
    _git(main, 'add', '.')
    _git(main, 'commit', '-q', '-m', 'init')
    subprocess.run([*GIT, 'worktree', 'add', '-q', str(tmp_path / 'worktrees' / 'w'), '-b', 'agent/w', 'main'], cwd=main, check=True)
    (tmp_path / 'worktrees' / 'w' / 'x.txt').write_text('x')
    _git(tmp_path / 'worktrees' / 'w', 'add', 'x.txt')
    _git(tmp_path / 'worktrees' / 'w', 'commit', '-q', '-m', 'work')
    return main


def _stub_srun(tmp_path, body):
    d = tmp_path / 'stubbin'
    d.mkdir()
    (d / 'srun').write_text('#!/bin/bash\n' + body)
    (d / 'srun').chmod(0o755)
    return d


# runs the command after the srun options (the first word that is not an option), as a real srun step would
RUN_STEP = textwrap.dedent('''\
    echo "$@" > "$SRUN_ARGS"
    while [ $# -gt 0 ]; do case "$1" in -*) shift ;; *) break ;; esac; done
    exec "$@"
    ''')


def _land(tmp_path, main, stubdir, **env):
    e = {**os.environ, 'PATH': f'{stubdir}:{os.environ["PATH"]}', 'SRUN_ARGS': str(tmp_path / 'srun.args'), 'ATLAS_LAND_RENEW_S': '1', **env}
    for k in [k for k in e if k.startswith('CS_ATLAS_') or k == 'ATLAS_LAND_TESTS_LOCAL']:
        if k not in env:
            del e[k]
    return subprocess.run(['bash', str(main / 'tools' / 'agent_worktree.sh'), 'land', 'w'], cwd=main, env=e, capture_output=True, text=True)


def _main_head(main):
    return _git(main, 'rev-parse', 'main').strip()


def test_success_runs_through_srun_and_lands(tmp_path):
    main = _fixture(tmp_path)
    before = _main_head(main)
    r = _land(tmp_path, main, _stub_srun(tmp_path, RUN_STEP))
    assert r.returncode == 0, r.stderr
    assert 'stub tests run on' in r.stdout and 'fast-forwarded' in r.stdout
    assert _main_head(main) != before
    args = (tmp_path / 'srun.args').read_text()
    for want in ('--partition=all', '--exclude=node302,node014,node805,node808', '--cpus-per-task=2', '--mem=8G', '--time=00:50:00', '--job-name=land-tests'):
        assert want in args
    assert 'srun wait' in r.stderr


def test_failing_tests_keep_main_and_a_nonzero_rc(tmp_path):
    main = _fixture(tmp_path)
    before = _main_head(main)
    r = _land(tmp_path, main, _stub_srun(tmp_path, RUN_STEP), STUB_TEST_RC='7')
    assert r.returncode == 1
    assert 'tests failed: main unchanged' in r.stdout
    assert _main_head(main) == before


def test_allocation_failure_stops_without_landing_or_calling_it_a_test_failure(tmp_path):
    main = _fixture(tmp_path)
    before = _main_head(main)
    r = _land(tmp_path, main, _stub_srun(tmp_path, 'echo "srun: error: Unable to allocate resources" >&2\nexit 1\n'))
    assert r.returncode == 3
    assert 'no test result' in r.stderr and 'main unchanged' in r.stderr
    assert 'tests failed' not in r.stdout
    assert _main_head(main) == before


def test_local_override_does_not_call_srun(tmp_path):
    main = _fixture(tmp_path)
    before = _main_head(main)
    r = _land(tmp_path, main, _stub_srun(tmp_path, 'echo called > "$SRUN_ARGS"\nexit 1\n'), ATLAS_LAND_TESTS_LOCAL='1')
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / 'srun.args').exists()
    assert _main_head(main) != before


def test_lock_is_renewed_while_the_step_waits(tmp_path):
    main = _fixture(tmp_path)
    (main / 'bin' / 'atlas').write_text(textwrap.dedent(f'''\
        #!/bin/bash
        case "$1 $2 $3" in
          "test  ") exit 0 ;;
          "task land-lock check") echo ours; exit 0 ;;
          "task land-lock acquire") echo acquire >> {tmp_path}/renewals; exit 0 ;;
        esac
        exit 0
        '''))
    _git(main, 'commit', '-qam', 'stub')
    _git(tmp_path / 'worktrees' / 'w', 'rebase', 'main')
    r = _land(tmp_path, main, _stub_srun(tmp_path, 'sleep 3\n' + RUN_STEP))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / 'renewals').read_text().count('acquire') >= 1
