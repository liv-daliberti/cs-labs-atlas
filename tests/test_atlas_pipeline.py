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
            assert kind in ('school', 'once') and py in ('project', 'collector') and cmd.startswith('PY ')
            assert ('{school}' in cmd) == (kind == 'school'), (name, stage)
