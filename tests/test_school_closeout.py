"""School closeout prevents moving-input reviews and resumes expensive work safely."""
import json
from types import SimpleNamespace

import pytest

import school_closeout as C


@pytest.fixture
def case(tmp_path, monkeypatch):
    data, out = tmp_path / 'data', tmp_path / 'run'
    data.mkdir(); out.mkdir()
    evidence = data / 'reviewed.json'
    evidence.write_text('{"approved": true}')
    monkeypatch.setattr(C.P, 'CODE', data)
    monkeypatch.setattr(C.P, 'HIERARCHY', data / 'hierarchy')
    monkeypatch.setattr(C.P, 'SCHOOL_CONFIGS', data / 'schools')
    monkeypatch.setattr(C.P, 'data', lambda name, *a: data / name)
    monkeypatch.setattr(C.P, 'data_w', lambda name, *a: data / name)
    monkeypatch.setattr(C, 'code_commit', lambda: 'a' * 40)
    monkeypatch.setenv('SLURM_JOB_ID', '123')
    seal = dict(school='u', code_commit='a' * 40, data_root=str(data), hierarchy=str(data / 'hierarchy'),
                school_configs=str(data / 'schools'), charter=None,
                inputs={str(evidence): dict(content=True, fingerprint=C.fingerprint(evidence))})
    C.write(out / 'inputs.json', seal)
    C.write(out / 'state.json', dict(status='sealed', phases=[], artifacts={}, submissions=[]))
    calls = []

    def run(argv, **kw):
        name = next(name for name, command in C.phases('u') if command == argv)
        calls.append(name)
        for output in C.OUTPUTS[name]:
            (data / output).write_text(json.dumps({'producer': name}))
        if name == 'build':
            C.write(data / 'report.json', {'provenance': {'code': {'commit': 'a' * 40, 'snapshot': True, 'dirty': False}}})
        return SimpleNamespace(returncode=0)

    return SimpleNamespace(data=data, out=out, evidence=evidence, run=run, calls=calls, seal=seal)


def passing(_school, stage):
    return dict(stage=int(stage), gate='pass', items=[])


def terminal(job='123', state='COMPLETED', exit_code='0:0'):
    return lambda *a, **kw: SimpleNamespace(stdout=f'{job}|{state}|{exit_code}|\n')


def test_native_checks_all_prerequisite_gates_on_one_build(case):
    seen = []

    def gates(school, stage):
        seen.append(int(stage))
        return dict(stage=int(stage), gate='fail' if stage in ('5', '7') else 'pass', items=[f'finding {stage}'])

    state = C.worker('u', case.out, run=case.run, evaluate=gates)
    assert case.calls == list(C.OUTPUTS)
    assert seen == list(C.GATES)
    assert state['status'] == 'gate_failed'
    assert state['gates']['5']['items'] and state['gates']['7']['items']
    with pytest.raises(ValueError, match='incomplete'):
        C.certify('u', case.out, run=terminal())
    assert not (case.out / 'draw-original.json').exists()


def test_late_phase_failure_resumes_without_rebuilding(case):
    def fail_diagnosis(argv, **kw):
        if 'link_diagnosis.py' in argv[1]:
            return SimpleNamespace(returncode=9)
        return case.run(argv, **kw)

    assert C.worker('u', case.out, run=fail_diagnosis, evaluate=passing)['status'] == 'phase_failed'
    assert case.calls == ['build', 'copies', 'ledger']
    assert C.worker('u', case.out, run=case.run, evaluate=passing)['status'] == 'awaiting_completion'
    assert case.calls == list(C.OUTPUTS)


def test_stale_or_dirty_builder_provenance_cannot_certify_a_new_build(case):
    def stale_report(argv, **kw):
        result = case.run(argv, **kw)
        if 'pi_hierarchy.py' in argv[1]:
            C.write(case.data / 'report.json', {'provenance': {'code': {'commit': 'old', 'snapshot': True}}})
        return result

    with pytest.raises(ValueError, match='Builder provenance differs'):
        C.worker('u', case.out, run=stale_report, evaluate=passing)
    assert case.calls == ['build']


def test_one_broken_gate_still_reports_other_gate_findings(case):
    seen = []

    def broken(school, stage):
        seen.append(stage)
        if stage == '3':
            raise ValueError('malformed website register')
        return passing(school, stage)

    state = C.worker('u', case.out, run=case.run, evaluate=broken)
    assert seen == [str(n) for n in C.GATES]
    assert state['status'] == 'gate_failed' and 'malformed website register' in state['gates']['3']['items'][0]


def test_changed_reviewed_content_blocks_any_new_native_work(case):
    case.evidence.write_text('{"approved":false}')
    with pytest.raises(ValueError, match='Inputs changed'):
        C.worker('u', case.out, run=case.run, evaluate=passing)
    assert case.calls == []


def test_missing_optional_input_added_after_seal_is_detected(case):
    optional = case.data / 'optional.json'
    case.seal['inputs'][str(optional)] = dict(content=True, fingerprint=None)
    optional.write_text('{}')
    assert str(optional) in C.changed_inputs(case.seal)


def test_snapshot_charter_location_can_change_but_its_bytes_cannot(case, monkeypatch):
    original = case.data / 'schools/u.toml'
    original.parent.mkdir()
    original.write_text('key="u"')
    case.seal['charter'] = C.fingerprint(original)
    C.write(case.out / 'inputs.json', case.seal)
    snapshot = case.data / 'snapshot/schools'
    snapshot.mkdir(parents=True)
    (snapshot / 'u.toml').write_bytes(original.read_bytes())
    monkeypatch.setattr(C.P, 'SCHOOL_CONFIGS', snapshot)
    C.validate_seal('u', case.out)
    (snapshot / 'u.toml').write_text('key="different"')
    with pytest.raises(ValueError, match='charter differs'):
        C.validate_seal('u', case.out)


def test_changed_artifact_restarts_at_its_producer(case):
    C.worker('u', case.out, run=case.run, evaluate=passing)
    state = C.read(case.out / 'state.json')
    (case.data / 'link-diagnosis.json').write_text('changed')
    assert C.resume_index(state) == 3
    with pytest.raises(ValueError):
        C.certify('u', case.out, run=terminal())
    C.worker('u', case.out, run=case.run, evaluate=passing)
    assert case.calls.count('build') == 1
    assert case.calls.count('diagnose') == 2


@pytest.mark.parametrize('state,exit_code', [('RUNNING', '0:0'), ('FAILED', '1:0'), ('COMPLETED', '1:0')])
def test_review_certification_requires_actual_terminal_success(case, state, exit_code):
    C.worker('u', case.out, run=case.run, evaluate=passing)
    with pytest.raises(ValueError, match='not completed successfully'):
        C.certify('u', case.out, run=terminal(state=state, exit_code=exit_code))
    assert not C.read(case.out / 'state.json')['ready_for_reviews']


def test_successful_certification_is_bound_to_exact_job_and_outputs(case):
    C.worker('u', case.out, run=case.run, evaluate=passing)
    with pytest.raises(ValueError):
        C.certify('u', case.out, run=terminal(job='999'))
    ready = C.certify('u', case.out, run=terminal())
    assert ready['ready_for_reviews'] and ready['slurm'] == ['123', 'COMPLETED', '0:0']


def test_draw_once_preserves_failed_prior_draw_and_never_rotates(case, monkeypatch):
    import student_recall as R
    C.worker('u', case.out, run=case.run, evaluate=passing)
    C.certify('u', case.out, run=terminal())
    prior = {'binds': {'old': 'hash'}, 'result': 'failed'}
    C.write(case.data / 'student-recall-check.json', prior)
    calls = []
    monkeypatch.setattr(R, 'bindings', lambda school: {'new': 'hash'})
    monkeypatch.setattr(R, 'draw', lambda school, drawn_by: calls.append((school, drawn_by)) or {'seed': 123, 'sample': [1, 2]})
    first = C.draw_once('u', case.out, 'drawer')
    assert C.draw_once('u', case.out, 'other') == first
    assert calls == [('u', 'drawer')]
    assert C.read(case.out / 'prior-recall.json') == prior
    C.write(case.out / 'draw-original.json', {'seed': 999, 'sample': [7]})
    with pytest.raises(ValueError, match='Original review draw changed'):
        C.draw_once('u', case.out, 'other')


def test_duplicate_submission_refused_but_timeout_can_resume():
    state = dict(status='running', submissions=[{'closeout': '123'}])
    for scheduler_state in ('PENDING', 'RUNNING', 'COMPLETED'):
        with pytest.raises(ValueError, match='no duplicate'):
            C.submission_available(state, run=terminal(state=scheduler_state))
    C.submission_available(state, run=terminal(state='TIMEOUT', exit_code='0:15'))


def test_repair_batch_requires_every_existing_review_receipt(tmp_path):
    receipt = tmp_path / 'approved.json'
    receipt.write_text('{"reviewed":true}')
    board = tmp_path / 'repairs.json'
    data = dict(school='u', cases=[dict(id='dates', status='open')])
    C.write(board, data)
    with pytest.raises(ValueError, match='Finish the repair batch'):
        C.repair_cases(board, 'u')
    data['cases'][0].update(status='resolved', receipt=dict(path=str(receipt), sha256=C.fingerprint(receipt)['sha256']))
    C.write(board, data)
    assert C.repair_cases(board, 'u') == data
    receipt.write_text('changed')
    with pytest.raises(ValueError, match='receipt missing or changed'):
        C.repair_cases(board, 'u')


def test_single_run_lock_prevents_two_writers(case):
    with C.locked(case.out):
        with pytest.raises(ValueError, match='Another closeout'):
            with C.locked(case.out):
                pytest.fail('second writer entered')
