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
