"""Owner ruling 2026-11-17: gates check correctness, not completeness (excluded_unresolved + audited sample; gate 1 coverage is a metric)."""
import json

import pytest

from tools import excluded_audit as EA
from tools import stage_gate as G


def row(name, decision='excluded_unresolved', **kw):
    d = dict(name=name, aliases=[], source='dblp_affiliation', decision=decision, reason='no source places the person',
             reason_code='no_source_covers_window', sources_tried=['CS_MAIN roster 2016-2026'])
    d.update(kw)
    return d


@pytest.fixture
def env(tmp_path, monkeypatch):
    state = dict(decisions=[row(f'P{i:03d}') for i in range(60)])
    monkeypatch.setattr(G.P, 'data', lambda name, key: tmp_path / name)
    monkeypatch.setattr(EA.P, 'data', lambda name, key: tmp_path / name)
    monkeypatch.setattr(G, 'sweep_gate', lambda k: [])
    (tmp_path / 'cs-related-candidates.json').write_text(json.dumps([{'name': d['name']} for d in state['decisions']]))

    def write():
        (tmp_path / 'cs-related-review.json').write_text(json.dumps(dict(decisions=state['decisions'])))

    write()
    return tmp_path, state, write


def verdicts(sample, fail=()):
    return [dict(name=n, verdict='fail' if n in fail else 'pass', evidence='checked') for n in sample]


def test_unresolved_excluded_still_needs_an_audit_and_counts_by_reason(env):
    _, _, _ = env
    bad, counts = G.g2('k')
    assert any('audit missing' in b for b in bad)
    assert counts['excluded_unresolved'] == 60 and counts['excluded_unresolved_by_reason'] == {'no_source_covers_window': 60}


def test_pass_with_a_reviewed_audit_and_the_sample_is_repeatable(env):
    _, _, _ = env
    a = EA.draw('k', 'worker-1', n=50, seed='s1')
    assert len(a['sample']) == 50 and a['seed'] == 's1'
    assert EA.draw('k', 'worker-1', n=50, seed='s1') == a                       # same population + seed: the same file/sample
    assert EA.pick(list(a['population']), 50, 's1', 'k') == a['sample']
    assert any('no independent reviewer' in b for b in G.g2('k')[0])
    with pytest.raises(SystemExit):
        EA.record('k', 'worker-1', verdicts(a['sample']))                      # the worker cannot review its own work
    EA.record('k', 'reviewer-2', verdicts(a['sample']))
    bad, counts = G.g2('k')
    assert bad == [] and counts['audit_failed'] == 0


def test_stale_when_the_review_changes_after_the_draw(env):
    _, state, write = env
    a = EA.draw('k', 'w', seed='s')
    EA.record('k', 'r', verdicts(a['sample']))
    state['decisions'][0]['reason'] = 'edited later'
    write()
    assert any('stale' in b for b in G.g2('k')[0])
    state['decisions'][0]['reason'] = 'no source places the person'
    state['decisions'].append(row('New Person'))
    write()
    (env[0] / 'cs-related-candidates.json').write_text(json.dumps([{'name': d['name']} for d in state['decisions']]))
    assert any('stale' in b for b in G.g2('k')[0])


def test_two_fixed_failures_pass_three_do_not_and_unfixed_failure_blocks(env):
    _, state, write = env
    a = EA.draw('k', 'w', seed='s')
    s = a['sample']
    EA.record('k', 'r', verdicts(s, fail=s[:2]))
    assert any('failed row' in b and 'still excluded' in b for b in G.g2('k')[0])
    for d in state['decisions']:
        if d['name'] in s[:2]:
            d['decision'] = 'accepted'
    write()
    assert G.g2('k')[0] == []                                                  # fixed rows left the class; the failures are recorded
    EA.record('k', 'r', verdicts(s, fail=s[:3]))
    for d in state['decisions']:
        if d['name'] == s[2]:
            d['decision'] = 'accepted'
    write()
    assert any('rework the class' in b for b in G.g2('k')[0])


def test_partial_verdicts_or_a_missing_reason_fail_closed(env):
    _, state, write = env
    a = EA.draw('k', 'w', seed='s')
    EA.record('k', 'r', verdicts(a['sample'][:-1]))
    assert any('do not cover' in b for b in G.g2('k')[0])
    state['decisions'][5].pop('sources_tried')
    write()
    assert any('without no sources_tried' in b for b in G.g2('k')[0])


def test_small_school_audits_everything(env):
    tmp, state, write = env
    state['decisions'] = state['decisions'][:7]
    write()
    a = EA.draw('k', 'w', seed='s')
    assert sorted(a['sample']) == sorted(d['name'] for d in state['decisions'])


def test_legacy_pending_still_blocks_until_converted_with_a_class(env):
    tmp, state, write = env
    state['decisions'][0].update(decision='pending_source_coverage')
    write()
    assert any('pending_source_coverage' in b for b in G.g2('k')[0])
    assert EA.convert('k') == {'no_source_covers_window': 1}
    doc = json.loads((tmp / 'cs-related-review.json').read_text())
    assert doc['decisions'][0]['decision'] == 'excluded_unresolved' and doc['decisions'][0]['converted_from'] == 'pending_source_coverage'


def test_collision_group_passes_when_each_identity_is_excluded_with_a_reason(env):
    tmp, state, write = env
    state['decisions'] = [row('Xiang Li', source_id='d1'), row('Xiang Li', source_id='d2')]
    cands = [dict(name='Xiang Li', dblp='d1'), dict(name='Xiang Li', dblp='d2')]
    (tmp / 'cs-related-candidates.json').write_text(json.dumps(cands))
    write()
    a = EA.draw('k', 'w', seed='s')
    EA.record('k', 'r', verdicts(a['sample']))
    # decisions are keyed by name in g2, but the collision check reads source ids
    bad = G.g2('k')[0]
    assert not any('share a display name' in b for b in bad)


def _g1(monkeypatch, tmp_path, cov, cfg=None):
    cfg = cfg or {'window': [2016, 2018], 'departments': [{'code': 'D'}]}
    monkeypatch.setattr(G.S, 'get', lambda k: cfg)
    monkeypatch.setattr(G.P, 'data', lambda name, key: tmp_path / name)
    (tmp_path / 'coverage.json').write_text(json.dumps(cov))
    return G.g1('k')


def test_gate1_partial_years_are_reported_not_blocking(monkeypatch, tmp_path):
    bad, counts = _g1(monkeypatch, tmp_path, {'D': {'2017': {'a H1': 'ok'}, '2016': {'a H1': 'nocapture: x'}}})
    assert bad == []
    assert counts['roster_coverage']['D']['partial_or_uncovered'] == ['2016: nocapture: x', '2018: never planned']
    assert counts['roster_years_open'] == 2


def test_gate1_fails_when_a_department_has_no_roster_source_at_all(monkeypatch, tmp_path):
    bad, _ = _g1(monkeypatch, tmp_path, {'D': {'2017': {'a H1': 'nocapture: x'}}})
    assert bad == ['D: no roster source in any window year (a department needs at least one)']


def test_gate1_roster_captured_outside_the_planner_is_reported_not_failed(monkeypatch, tmp_path):
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': [{'name': 'A', 'listed_in': ['D'], 'years_listed': [2016, 2017]}]}))
    bad, counts = _g1(monkeypatch, tmp_path, {})
    assert bad == [] and counts['roster_coverage']['D']['captured_outside_planner_years'] == [2016, 2017]
    (tmp_path / 'census-faculty.json').write_text(json.dumps({'faculty': []}))
    assert _g1(monkeypatch, tmp_path, {})[0] == ['D: no roster source in any window year (a department needs at least one)']
