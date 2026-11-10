"""Disk guard (2026-11-10): a low df reading touches the stop marker and scancels our download jobs by name; loops refuse to start / resubmit while it exists."""
import fcntl
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

CODE = Path(__file__).resolve().parents[1]
FT = CODE / 'fulltext-push'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DG = load('disk_guard', FT / 'disk_guard.py')


def fake_run(free, calls):
    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == 'df':
            return SimpleNamespace(stdout=f'Avail\n{free}\n', returncode=0)
        return SimpleNamespace(stdout='', returncode=0)
    return run


def test_above_limit_does_nothing(tmp_path):
    calls = []
    rec = DG.check('/x', tmp_path / 'm', 250, run=fake_run(800, calls))
    assert 'action' not in rec and not (tmp_path / 'm').exists()
    assert all(c[0] == 'df' for c in calls)


def test_below_limit_marks_and_cancels_by_name(tmp_path):
    calls = []
    rec = DG.check('/x', tmp_path / 'raw' / 'm', 250, names=('school-fulltext', 'etd-crawl'), run=fake_run(240, calls))
    assert rec['action'] == 'stopping downloads' and (tmp_path / 'raw' / 'm').exists()
    scancels = [c for c in calls if c[0] == 'scancel']
    assert [c[1] for c in scancels] == ['--name=school-fulltext', '--name=etd-crawl'] and all('-u' in c for c in scancels)


def test_default_names_are_ours_only():
    assert 'school-fulltext' in DG.DEFAULT_JOB_NAMES and all('oxford' not in n for n in DG.DEFAULT_JOB_NAMES)
    assert DG.LIMIT_GB == 250 and DG.INTERVAL_S == 120


def test_free_gb_parses_df():
    assert DG.free_gb('/x', fake_run(802, [])) == 802


def run_bash(script, env):
    return subprocess.run(['bash', '-c', script], capture_output=True, text=True, env=env)


def test_loop_job_refuses_while_marker_exists(tmp_path):
    env = {'PATH': '/usr/bin:/bin', 'CS_ATLAS_FT_RAW': str(tmp_path), 'CS_ATLAS_CODE': str(tmp_path)}
    src = f'. {FT}/loop_job.sh; refuse_if_downloads_stopped; echo started'
    assert 'started' in run_bash(src, env).stdout
    (tmp_path / 'downloads_stopped_by_disk_guard').write_text('{}')
    r = run_bash(src, env)
    assert r.returncode == 3 and 'started' not in r.stdout and 'refused' in r.stdout


def test_collector_scripts_check_the_marker():
    for f in ('school-collector.slurm', 'michigan-collector.slurm', 'downloads.slurm'):
        assert 'refuse_if_downloads_stopped' in (FT / f).read_text(), f
    assert 'LOOP_RESUBMIT_IGNORE_STOP' in (FT / 'disk-guard.slurm').read_text()


def test_lock_wait_retries_then_gives_up(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(FT))
    import lab_first_loop as L
    p = tmp_path / 'lock'
    a, b = open(p, 'a'), open(p, 'a')
    fcntl.flock(a, fcntl.LOCK_EX)
    # released after two retries -> acquired
    n = {'i': 0}

    def sleep(s):
        n['i'] += 1
        if n['i'] == 2:
            fcntl.flock(a, fcntl.LOCK_UN)
    assert L.acquire_lock(b, 60, 0.01, sleep=sleep) is True and n['i'] == 2
    fcntl.flock(b, fcntl.LOCK_UN)
    fcntl.flock(a, fcntl.LOCK_EX)
    assert L.acquire_lock(b, 0.0, 0.01, sleep=lambda s: None) is False
