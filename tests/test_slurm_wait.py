"""ROADMAP #35: waiting is one sacct call per >= 120 s, ends on the first failed job, backs off on errors; pipeline and release --wait use it."""
import pytest

import atlas_pipeline as AP
import atlas_release as AR
import slurm_wait as W


@pytest.fixture(autouse=True)
def no_live_release_lock(monkeypatch):
    """submit_and_wait refuses while a real release holds the atlas-release lease (2026-11-03: a live release made this file fail);
    the tests are about the submit/wait protocol, so they never read the live lease."""
    monkeypatch.setattr(AR, 'lock_holder', lambda root=None: None)


class Sacct:
    """Scripted sacct: each call returns the next listing (or fails)."""
    def __init__(self, *listings):
        self.listings, self.calls = list(listings), []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        item = self.listings.pop(0)

        class R:
            returncode = 0 if item is not None else 1
            stdout = item or ''
            stderr = 'slurm_load_jobs error'
        return R()


def test_waits_with_one_call_per_interval_until_all_complete():
    run, naps = Sacct('', '10|a|RUNNING|0:0', '10|a|COMPLETED|0:0\n11_0|b|PENDING|0:0', '10|a|COMPLETED|0:0\n11_0|b|COMPLETED|0:0\n11_1|b|COMPLETED|0:0'), []
    v, st = W.wait(['10', '11'], run=run, sleep=naps.append)
    assert v == 'ok' and len(run.calls) == 4 and naps == [120, 120, 120]
    assert all(c[:2] == ['sacct', '-j'] and c[2] == '10,11' for c in run.calls)


def test_interval_is_never_below_120_and_failure_ends_the_wait():
    run, naps = Sacct('10|a|RUNNING|0:0', '10|a|FAILED|1:0\n11|b|PENDING|0:0'), []
    v, st = W.wait(['10', '11'], interval=5, run=run, sleep=naps.append)
    assert v == 'failed' and naps == [120] and st['10'][1] == 'FAILED'


def test_sacct_errors_back_off_instead_of_retrying_faster():
    run, naps = Sacct(None, None, None, '10|a|COMPLETED|0:0'), []
    v, _ = W.wait(['10'], run=run, sleep=naps.append)
    assert v == 'ok' and naps == [240, 480, 900]


def test_cancelled_by_user_is_a_failure():
    assert W.verdict({'10': ('a', 'CANCELLED', '0:0')}, ['10']) == 'failed'
    assert W.states(['1'], run=Sacct('1|a|CANCELLED by 5|0:0'))['1'][1] == 'CANCELLED'


def test_pipeline_wait_uses_slurm_wait_not_scontrol(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(AP.P, 'SCRATCH', tmp_path)
    monkeypatch.setattr(AP, 'submit', lambda *a, **k: {'reader': '77'})
    got = {}
    monkeypatch.setattr(W, 'wait', lambda ids, run=None, **k: got.update(ids=ids) or ('failed', {'77': ('x', 'FAILED', '1:0')}))
    calls = []
    assert AP.main(['reader', '--wait'], run=lambda argv, **kw: calls.append(argv)) == 1
    assert got['ids'] == ['77'] and not any('scontrol' in c for c in calls)


@pytest.fixture(autouse=True)
def private_release_lock(tmp_path, monkeypatch):
    """A release job running these tests holds the REAL atlas-release lease (the preflight caught this, 2026-11-03): look at a private lease directory."""
    monkeypatch.setattr(AR, 'LEASE_ROOT', tmp_path / 'leases')


def test_release_wait_submits_the_job_pinned_and_waits(monkeypatch):
    calls = []

    def run(argv, **kw):
        calls.append((argv, kw.get('env') or {}))

        class R:
            returncode, stderr = 0, ''
            stdout = 'abc123\n' if argv[0] == 'git' else '4242'
        return R()
    monkeypatch.setattr(W, 'wait', lambda ids, run=None, **k: ('ok', {'4242': ('cs-release', 'COMPLETED', '0:0')}))
    rc = AR.submit_and_wait(['--yes-push', '--only', 'rebuild,validate'], run=run, wait=W.wait)
    assert rc == 0
    probe, real = calls[1], calls[2]
    assert '--test-only' in probe[0] and '--test-only' not in real[0]
    assert real[1]['CS_ATLAS_SNAPSHOT_COMMIT'] == 'abc123' and real[1]['RELEASE_ARGS'] == '--yes-push --only rebuild,validate'


def test_release_wait_refuses_on_preempts():
    def run(argv, **kw):
        class R:
            returncode, stdout = 0, 'git'
            stderr = 'sbatch: Job 1 to start at ... Preempts: 5' if '--test-only' in argv else ''
        return R()
    assert AR.submit_and_wait([], run=run) == 1


def test_release_wait_with_dry_run_does_not_submit(monkeypatch):
    monkeypatch.setattr(AR, 'submit_and_wait', lambda *a, **k: pytest.fail('submitted'))
    assert AR.main(['--wait', '--dry-run', '--tag', 'tdry']) == 0
