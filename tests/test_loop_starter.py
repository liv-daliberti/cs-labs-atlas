"""loop_starter: a school starts only when warm, unmarked, its recorded loop job is not live and its loop lock is free."""
import fcntl
import json
from types import SimpleNamespace

import loop_starter as L


def store(tmp_path, warm=True, job=None):
    s = tmp_path / 'st'
    s.mkdir(exist_ok=True)
    if warm:
        (s / '.copy-quality-warm.json').write_text('{}')
    if job:
        (s / 'loop-state.json').write_text(json.dumps(dict(slurm_job=job)))
    return s


def test_not_warm(tmp_path):
    assert L.ready('x', store(tmp_path, warm=False), set(), tmp_path) == 'cache not warm'


def test_marker_and_squeue_failure(tmp_path):
    s = store(tmp_path)
    assert L.ready('x', s, None, tmp_path) == 'squeue failed'
    (tmp_path / L.MARKER).write_text('')
    assert L.ready('x', s, set(), tmp_path) == 'disk guard marker'


def test_live_job_and_lock(tmp_path):
    s = store(tmp_path, job='77')
    assert L.ready('x', s, {'77'}, tmp_path) == 'its loop job is still live'
    held = open(s / '.loop.lock', 'a')
    fcntl.flock(held, fcntl.LOCK_EX)
    assert L.ready('x', s, set(), tmp_path) == 'loop lock held'
    fcntl.flock(held, fcntl.LOCK_UN)
    assert L.ready('x', s, set(), tmp_path) is None


def fake(outs):
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw['env']['SCHOOL'], kw['env']['CHANNELS']))
        return outs.pop(0)
    return run, calls


def test_submit_tests_first_then_submits(tmp_path):
    ok = SimpleNamespace(returncode=0, stdout='sbatch: Job 1 to start', stderr='')
    done = SimpleNamespace(returncode=0, stdout='Submitted batch job 4242', stderr='')
    run, calls = fake([ok, done])
    assert L.submit('mit', 'oa_arxiv pmc', run, str(tmp_path)) == '4242'
    assert '--test-only' in calls[0][0] and '--test-only' not in calls[1][0] and calls[1][1:] == ('mit', 'oa_arxiv pmc')


def test_preempts_refuses(tmp_path):
    bad = SimpleNamespace(returncode=0, stdout='Preempts: 5', stderr='')
    run, calls = fake([bad])
    assert L.submit('mit', 'x', run, str(tmp_path)) is None and len(calls) == 1


def test_submit_does_not_inherit_this_jobs_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv('SNAPSHOT_REPO', '/x/worktree')
    monkeypatch.setenv('CS_ATLAS_SNAPSHOT_COMMIT', 'abc')
    seen = []

    def run(cmd, **kw):
        seen.append(kw['env'])
        return SimpleNamespace(returncode=0, stdout='Submitted batch job 9', stderr='')
    L.submit('mit', 'x', run, str(tmp_path))
    assert all('SNAPSHOT_REPO' not in e and 'CS_ATLAS_SNAPSHOT_COMMIT' not in e for e in seen)
