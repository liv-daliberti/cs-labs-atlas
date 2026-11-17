"""Audit reuse retains producer provenance and refuses scientific or reviewed-input drift."""
from pathlib import Path
from types import SimpleNamespace
import pytest
import school_closeout as C


@pytest.fixture
def parent(tmp_path, monkeypatch):
    data=tmp_path/'data'; data.mkdir(); old=tmp_path/'old'; old.mkdir()
    evidence=data/'reviewed.json'; evidence.write_text('{"approved":true}')
    monkeypatch.setattr(C.P,'CODE',data); monkeypatch.setattr(C.P,'HIERARCHY',data/'hierarchy'); monkeypatch.setattr(C.P,'SCHOOL_CONFIGS',data/'schools')
    monkeypatch.setattr(C.P,'data',lambda name,*a: data/name)
    monkeypatch.setattr(C,'code_commit',lambda:'b'*40)
    monkeypatch.setattr(C,'input_specs',lambda school:{str(evidence):dict(content=True)})
    for names in C.OUTPUTS.values():
        for name in names: (data/name).write_text('{}')
    C.write(data/'report.json',dict(provenance=dict(code=dict(commit='a'*40,snapshot=True,dirty=False))))
    seal=dict(school='u',code_commit='a'*40,data_root=str(data),hierarchy=str(data/'hierarchy'),charter=None,inputs={str(evidence):dict(content=True,fingerprint=C.fingerprint(evidence))})
    artifacts={}
    for phase in C.OUTPUTS: artifacts.update(C.capture_outputs('u',phase))
    C.write(old/'inputs.json',seal); C.write(old/'state.json',dict(status='gate_failed',phases=list(C.OUTPUTS),artifacts=artifacts,submissions=[],job='123'))
    state=SimpleNamespace(data=data,old=old,new=tmp_path/'new',evidence=evidence,delta='tools/link_diagnosis.py\ntools/chain_audit.py\ntools/school_closeout.py\n',dirty='',terminal='123|FAILED|1:0|\n',old_control='def worker(): return 1',new_control='def worker(): return 1')
    def run(argv,**kw):
        if argv[0]=='sacct': out=state.terminal
        elif 'status' in argv: out=state.dirty
        elif 'diff' in argv: out=state.delta
        elif 'show' in argv: out=state.old_control if argv[-1].startswith('a'*40) else state.new_control
        else: raise AssertionError(argv)
        return SimpleNamespace(stdout=out,returncode=0)
    state.run=run
    return state


def test_refresh_runs_only_audits_retaining_native_bytes_and_provenance(parent,monkeypatch):
    p=parent; original=(p.old/'state.json').read_bytes(); native={name:(p.data/name).read_bytes() for name in C.OUTPUTS['build']}
    seal=C.fork_audits('u',p.old,p.new,run=p.run)
    assert seal['code_commit']=='b'*40 and seal['audit_refresh']['native_code_commit']=='a'*40
    assert (p.old/'state.json').read_bytes()==original
    assert C.resume_index(C.read(p.new/'state.json'))==3
    calls=[]; monkeypatch.setenv('SLURM_JOB_ID','456')
    def produce(argv,**kw):
        phase=next(name for name,args in C.phases('u') if args==argv); calls.append(phase)
        for name in C.OUTPUTS[phase]: (p.data/name).write_text('{"refreshed":true}')
        return SimpleNamespace(returncode=0)
    result=C.worker('u',p.new,run=produce,evaluate=lambda s,g:dict(gate='pass'))
    assert result['status']=='awaiting_completion' and calls==['diagnose','students']
    assert all((p.data/name).read_bytes()==raw for name,raw in native.items())


@pytest.mark.parametrize('failure', ['input','new_input','native','builder','controls','dirty','draw','live','provenance'])
def test_refresh_refuses_drift_or_unfinished_review_parent(parent,monkeypatch,failure):
    p=parent
    if failure=='input': p.evidence.write_text('{"approved":false}')
    elif failure=='new_input': monkeypatch.setattr(C,'input_specs',lambda s:{'new-unsealed-input':{}})
    elif failure=='native': (p.data/'students.json').write_text('changed')
    elif failure=='builder': p.delta+='tools/pihier/papers.py\n'
    elif failure=='controls': p.new_control='def worker(): return 2'
    elif failure=='dirty': p.dirty=' M tools/chain_audit.py'
    elif failure=='draw': (p.old/'draw-original.json').write_text('{}')
    elif failure=='live': p.terminal='123|RUNNING|0:0|\n'
    elif failure=='provenance': C.write(p.data/'report.json',dict(provenance=dict(code=dict(commit='wrong',snapshot=True,dirty=False))))
    with pytest.raises(ValueError): C.fork_audits('u',p.old,p.new,run=p.run)
    assert not p.new.exists()


def test_actual_refresh_additions_leave_existing_producer_controls_identical():
    source=Path(C.__file__).read_text()
    assert C.audit_control_tree(source)==C.audit_control_tree(source.replace("'fork-audits'", "'extra-audit-command'"))
    assert C.audit_control_tree(source)!=C.audit_control_tree(source.replace("GATES = " + repr(C.GATES), "GATES = (1, 2)"))
