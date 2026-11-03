"""atlas_cli: the `atlas <command>` dispatcher."""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]


def test_dispatcher_lists_commands():
    out = subprocess.run([sys.executable, '-m', 'atlas_cli', 'help'], cwd=CODE, capture_output=True, text=True, check=True).stdout
    for c in ('build', 'release', 'copies', 'ledger', 'stage-gate', 'collect', 'test'):
        assert f'  {c} ' in out


def test_bin_atlas_reads_the_checkouts_own_charters():
    """A charter made in a worktree must be visible to `atlas charters` and the stage tools run from that worktree."""
    out = subprocess.run([str(CODE / 'bin' / 'atlas'), 'paths', 'SCHOOL_CONFIGS'], cwd=CODE, capture_output=True, text=True, check=True,
                         env={k: v for k, v in __import__('os').environ.items() if k != 'CS_ATLAS_SCHOOL_CONFIGS'}).stdout
    assert str(CODE / 'schools') in out


def test_submit_pins_main_or_the_worktrees_own_commit(tmp_path):
    import atlas_cli as A
    def git(d, *a):
        subprocess.run(['git', '-C', str(d), *a], check=True, capture_output=True)
    main = tmp_path / 'main'; main.mkdir()
    git(main, 'init', '-q', '-b', 'main'); git(main, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'm')
    wt = tmp_path / 'wt'
    git(main, 'worktree', 'add', '-q', str(wt), '-b', 'agent/x')
    git(wt, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'w')
    head = lambda d: subprocess.run(['git', '-C', str(d), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    pins, rest = A.submit_pins(wt, main, ['--time=1', 'x.slurm'])
    assert pins == {'CS_ATLAS_SNAPSHOT_COMMIT': head(main)} and rest == ['--time=1', 'x.slurm']       # the default is unchanged
    pins, rest = A.submit_pins(wt, main, ['--from-worktree', 'x.slurm'])
    assert pins == {'CS_ATLAS_SNAPSHOT_COMMIT': head(wt), 'SNAPSHOT_REPO': str(wt)} and rest == ['x.slurm'] and head(wt) != head(main)


def test_bin_atlas_uses_its_own_atlas_cli_whatever_the_cwd(tmp_path):
    """`atlas` run from another checkout's directory must not import that directory's atlas_cli (python -m puts cwd first)."""
    (tmp_path / 'atlas_cli').mkdir()
    (tmp_path / 'atlas_cli' / '__init__.py').write_text('raise SystemExit("imported the caller\'s atlas_cli")\n')
    (tmp_path / 'atlas_cli' / '__main__.py').write_text('')
    out = subprocess.run([str(CODE / 'bin' / 'atlas'), 'help'], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0 and 'usage: atlas' in out.stdout
