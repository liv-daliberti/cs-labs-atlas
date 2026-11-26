"""stage_audit: seeded draw, independent reviewer, invalidation only on input change, fail closed, failed rows hold their PI."""
import json

import pytest

import stage_audit as SA


@pytest.fixture
def env(tmp_path, monkeypatch):
    pop = {f'P{i}': (f'fp{i}', {}) for i in range(60)}
    state = dict(pop=pop, doc=None)
    monkeypatch.setitem(SA.POPULATIONS, 'homes', lambda key: state['pop'])
    monkeypatch.setattr(SA, 'load', lambda key, cls: state['doc'])
    monkeypatch.setattr(SA, 'save', lambda key, cls, doc: state.update(doc=json.loads(json.dumps(doc))))
    return state


def verdicts(doc, fail=()):
    return [dict(name=k, verdict='fail' if k in fail else 'pass', evidence='read it', fixed=False) for k in doc['sample']]


def test_draw_is_seeded_and_stable(env):
    d1 = SA.draw('x', 'homes', 'w1')
    d2 = SA.draw('x', 'homes', 'w2')           # a repeat draw of an unchanged population is the same file, not a new draw per attempt
    assert d1['sample'] == d2['sample'] and len(d1['sample']) == 50 and d2['worker'] == 'w1' and d1['sample_hash']


def test_missing_then_unreviewed_then_pass(env):
    assert 'missing' in SA.findings('x', 'homes')[0][0]
    d = SA.draw('x', 'homes', 'w')
    assert 'no independent reviewer' in SA.findings('x', 'homes')[0][0]
    with pytest.raises(SystemExit):
        SA.record('x', 'homes', 'w', verdicts(d))   # the worker cannot review their own rows
    SA.record('x', 'homes', 'r', verdicts(d))
    assert SA.findings('x', 'homes')[0] == []
    assert all(v['reviewed_by'] == 'r' and v['seed'] == d['seed'] and v['sample_hash'] == d['sample_hash'] for v in env['doc']['verdicts'])


def test_stale_only_when_inputs_change(env):
    d = SA.draw('x', 'homes', 'w')
    SA.record('x', 'homes', 'r', verdicts(d))
    env['pop']['P0'] = ('changed', {})
    assert 'stale' in SA.findings('x', 'homes')[0][0]
    env['pop']['P0'] = ('fp0', {})
    assert SA.findings('x', 'homes')[0] == []


def test_failed_rows_hold_their_pi_until_fixed_and_more_than_two_rework(env):
    d = SA.draw('x', 'homes', 'w')
    bad = d['sample'][:2]
    SA.record('x', 'homes', 'r', verdicts(d, fail=bad))
    items = SA.findings('x', 'homes')[0]
    assert len(items) == 2 and all(i.startswith(tuple(bad)) and 'not fixed' in i for i in items)   # the item names the PI: pi_states holds that PI only
    env['pop'][bad[0]] = ('fixed', {})
    del env['pop'][bad[1]]
    assert SA.findings('x', 'homes')[0] == []      # fixed rows may change or leave without making the draw stale
    SA.record('x', 'homes', 'r', verdicts(d, fail=d['sample'][:3]))
    assert any('rework the class' in i for i in SA.findings('x', 'homes')[0])


def test_review_page_lists_the_draw(env):
    d = SA.draw('x', 'homes', 'w')
    page = SA.review_page('x', 'homes')
    assert d['sample'][0] in page and d['seed'] in page and 'Verdict file' in page


def test_released_school_is_not_enforced(monkeypatch):
    import school_config as S
    monkeypatch.setattr(S, 'get', lambda key: dict(status='released'))
    assert SA.items('x', 3) == ([], {})


def test_every_audit_class_has_a_registered_data_path():
    """2026-11-17: g3 crashed with KeyError 'audit-homes.json is not in atlas_paths.DATA_FILES' for every school."""
    import stage_audit as SA
    for cls in SA.CLASSES:
        if cls == 'excluded':
            continue
        assert SA.json_path('purdue', cls).name == f'audit-{cls}.json'


def test_sjtu_owner_waiver_records_actual_reviewer_and_keeps_other_bars(env):
    worker = 'codex-sjtu-stage9-1124'
    doc = SA.draw('sjtu', 'homes', worker)
    SA.record('sjtu', 'homes', worker, verdicts(doc))
    assert env['doc']['reviewer'] == env['doc']['worker'] == worker
    assert env['doc']['owner_independence_waiver']['decision'] == 'D-0061'
    assert SA.findings('sjtu', 'homes')[0] == []
    saved = env['doc'].pop('owner_independence_waiver')
    assert any('no independent reviewer' in x for x in SA.findings('sjtu', 'homes')[0])
    env['doc']['owner_independence_waiver'] = saved
    SA.record('sjtu', 'homes', worker, verdicts(doc, fail=doc['sample'][:3]))
    assert any('rework the class' in x for x in SA.findings('sjtu', 'homes')[0])
    SA.record('sjtu', 'homes', worker, verdicts(doc))
    env['pop']['P0'] = ('changed', {})
    assert any('stale' in x for x in SA.findings('sjtu', 'homes')[0])


@pytest.mark.parametrize(('school', 'stage', 'worker', 'reviewer'), [
    ('other', 3, 'codex-sjtu-stage9-1124', 'codex-sjtu-stage9-1124'),
    ('sjtu', 2, 'codex-sjtu-stage9-1124', 'codex-sjtu-stage9-1124'),
    ('sjtu', 3, 'another-worker', 'another-worker'),
])
def test_sjtu_owner_waiver_is_not_a_general_self_review_permission(school, stage, worker, reviewer):
    assert SA.owner_independence_waiver(school, stage, worker, reviewer) is None


def test_identity_draw_always_includes_owned_per_work_rows(monkeypatch):
    pop = {f'P{i}': (f'fp{i}', {'no_identity': True}) for i in range(80)}
    pop['W1'] = ('fpw1', {'owned_per_work_only': True})
    pop['W2'] = ('fpw2', {'owned_per_work_only': True})
    monkeypatch.setattr(SA, 'population', lambda key, cls: pop)
    fp = {k: v[0] for k, v in pop.items()}
    for seed in ('a', 'b', 'c'):
        s = SA.drawn_sample('k', 'identity', fp, 50, seed)
        assert len(s) == 50 and {'W1', 'W2'} <= set(s)
        assert s == SA.drawn_sample('k', 'identity', fp, 50, seed)
    assert SA.must_draw('homes', {k: v[1] for k, v in pop.items()}) == []
