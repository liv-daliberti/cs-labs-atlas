"""ROADMAP #33: a stage is stale when an output is missing, an input is newer than the oldest output, or its code is newer; fresh stages are skipped."""
import os

import pytest

import stale_stages as T


def touch(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('x')
    os.utime(p, (t, t))


def setup(monkeypatch, tmp_path, outs, ins, code=0):
    paths = {}

    def dp(name, school):
        return tmp_path / f'{school}-{name}'
    monkeypatch.setattr(T, 'data_path', dp)
    monkeypatch.setattr(T, 'input_paths', lambda spec, school: [tmp_path / f'{school}-{n}' for n in ins])
    monkeypatch.setattr(T, 'code_time', lambda files: code)
    monkeypatch.setitem(T.STAGES, 'copies', ('school', [], ['tools/x.py'], outs))
    return paths


def test_missing_output_is_stale(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, ['copies.json'], ['in.json'])
    touch(tmp_path / 'mit-in.json', 100)
    assert T.check('copies', 'mit') == (True, 'an output is missing: mit-copies.json')


def test_newer_input_and_newer_code_make_it_stale_otherwise_fresh(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, ['copies.json'], ['in.json'])
    touch(tmp_path / 'mit-copies.json', 200)
    touch(tmp_path / 'mit-in.json', 100)
    assert T.check('copies', 'mit') == (False, 'fresh')
    touch(tmp_path / 'mit-in.json', 300)
    assert T.check('copies', 'mit') == (True, 'an input is newer than the oldest output')
    touch(tmp_path / 'mit-in.json', 100)
    monkeypatch.setattr(T, 'code_time', lambda files: 250)
    assert T.check('copies', 'mit') == (True, 'its code was committed after the oldest output')


def test_stage_list_drags_later_stages_and_adds_the_checks():
    fresh = {s: dict(stale=False, schools=[], why={}) for s in T.ORDER}
    assert T.stage_list(fresh) == []
    fresh['copies'] = dict(stale=True, schools=['mit'], why={'mit': 'x'})
    got = T.stage_list(fresh)
    assert got[:4] == ['snapshot', 'copies', 'ledger', 'reader'] and got[4:] == T.ALWAYS and 'build' not in got


@pytest.mark.parametrize('name', T.NATIVE_UPSTREAM_INPUTS)
def test_upstream_product_change_requires_native_rebuild(monkeypatch, tmp_path, name):
    monkeypatch.setattr(T.P, 'data', lambda n, school: tmp_path / f'{school}-{n}')
    monkeypatch.setattr(T.P, 'SITE_DATA', tmp_path / 'site')
    monkeypatch.setattr(T, 'raw_reviewed_names', lambda: [])
    for output in T.BUILD_OUT:
        touch(tmp_path / f'u-{output}', 200)
    upstream = tmp_path / f'u-{name}'
    touch(upstream, 100)
    assert T.check('build', 'u', ctime=0) == (False, 'fresh')
    touch(upstream, 300)
    assert T.check('build', 'u', ctime=0) == (True, 'an input is newer than the oldest output')


def test_fallback_collection_is_an_input_only_when_used(monkeypatch, tmp_path):
    monkeypatch.setattr(T.P, 'data', lambda n, school: tmp_path / n)
    monkeypatch.setattr(T.P, 'SITE_DATA', tmp_path / 'site')
    fallback = tmp_path / 'site/collection-u.json.gz'
    assert fallback in T.native_upstream_paths('u')
    touch(tmp_path / 'collection.json.gz', 100)
    assert fallback not in T.native_upstream_paths('u')
