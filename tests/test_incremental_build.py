import pytest

from incremental_build import OUTPUTS, run_school


def test_unchanged_school_is_reused_but_input_and_output_changes_rebuild(tmp_path):
    state, calls = {'reviewed': 'first'}, []
    def build(school):
        calls.append(school)
        for name in OUTPUTS[:5]:
            (tmp_path / name).write_text(str(len(calls)))
    run = lambda **kw: run_school('school', build, directory=tmp_path, input_state=lambda _: dict(state), **kw)
    assert run()['action'] == 'built'
    assert run()['action'] == 'reused'
    state['reviewed'] = 'corrected'
    assert run()['action'] == 'built'
    (tmp_path / 'students.json').write_text('changed externally')
    assert run()['action'] == 'built'
    assert run(force=True)['action'] == 'built'
    assert len(calls) == 4


def test_input_drift_cannot_receive_a_reusable_receipt(tmp_path):
    state = {'raw': 'before'}
    def build(_):
        state['raw'] = 'during build'
    with pytest.raises(RuntimeError, match='inputs changed'):
        run_school('school', build, directory=tmp_path, input_state=lambda _: dict(state))
    assert not (tmp_path / '.incremental-build.json').exists()


def test_school_scopes_are_separate(tmp_path):
    state = {'a': 1, 'b': 1}
    calls = []
    def run(school):
        d = tmp_path / school
        def build(s):
            calls.append(s)
            for name in OUTPUTS[:5]:
                (d / name).write_text('data')
        return run_school(school, build, directory=d, input_state=lambda s: {'source': state[s]})
    run('a'); run('b')
    state['a'] = 2
    assert run('a')['action'] == 'built'
    assert run('b')['action'] == 'reused'
    assert calls == ['a', 'b', 'a']
