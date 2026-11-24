"""tools/work_queue.py: overlap refusal, expiry, the land lock, concurrent claims under flock, the CLI exit codes."""
import datetime
import json
import multiprocessing as mp

import agent_lease as AL
import work_queue as W


def _add(root, title, school='', kind='build', scope=(), tid=None):
    return W.add(title, school, kind, scope, tid, root=root)[1]['id']


def test_overlap_by_scope_title_and_school_kind_is_refused_with_the_holder(tmp_path):
    a = _add(tmp_path, 'Toronto census', 'toronto', 'collect', ['hierarchy/toronto'])
    b = _add(tmp_path, 'Toronto faculty pages', 'toronto', 'collect', ['listings/toronto'])      # disjoint scope, same school+kind
    c = _add(tmp_path, 'Other', 'oxford', 'build', ['hierarchy/toronto/raw'])                      # scope under the holder's
    d = _add(tmp_path, 'Totally different', 'oxford', 'review', ['tools/x.py'])
    assert W.claim(a, 'claude', 'agent/toronto', root=tmp_path)[0]
    for t, why in ((b, 'same school and kind'), (c, 'overlaps')):
        ok, task, cs = W.claim(t, 'codex', root=tmp_path)
        assert not ok and cs[0][0]['id'] == a and cs[0][0]['branch'] == 'agent/toronto' and why in cs[0][1]
    assert W.claim(d, 'codex', root=tmp_path)[0]
    assert W.claim(a, 'claude', root=tmp_path)[0]                                                  # the holder may re-claim
    ok, _, cs = W.claim(b, 'codex', allow_overlap='disjoint rosters', root=tmp_path)
    assert ok and 'allow-overlap' in W.find(W.load(tmp_path), b)['history'][-1]['note']
    assert W.claim(a, 'codex', root=tmp_path)[2][0][1] == 'already claimed'


def test_same_title_is_refused_at_add_and_at_claim(tmp_path):
    a = _add(tmp_path, 'Co-adviser rule')
    assert W.add('co-adviser  RULE!', root=tmp_path)[0] is False
    tasks = W.load(tmp_path); tasks.append(W.make(tasks, 'Co-adviser rule', tid='T900')); W.save(tasks, tmp_path)   # a duplicate made behind add's back
    assert W.claim(a, 'claude', root=tmp_path)[0]
    assert 'same title' in W.claim('T900', 'codex', root=tmp_path)[2][0][1]


def test_stale_claim_expires_and_heartbeat_keeps_it(tmp_path):
    a = _add(tmp_path, 'Long job review', 'mit', 'review', ['hierarchy/mit'])
    W.claim(a, 'claude', ttl=60, root=tmp_path)

    def age(sec):
        ts = W.load(tmp_path); ts[0]['heartbeat'] = W.stamp(W.now() - datetime.timedelta(seconds=sec)); W.save(ts, tmp_path)
    age(120)
    t = W.load(tmp_path)[0]
    assert not W.live(t) and W.state(t) == 'stale'
    b = _add(tmp_path, 'Another', 'mit', 'review', ['hierarchy/mit/x'])
    assert W.claim(b, 'codex', root=tmp_path)[0]                                                    # stale holder no longer blocks
    age(10)
    t = W.update(a, 'claude', event='heartbeat', root=tmp_path)
    assert W.live(t) and t['heartbeat'] > W.stamp(W.now() - datetime.timedelta(seconds=5))
    ok, _, cs = W.claim(a, 'codex', root=tmp_path)
    assert not ok                                                                                    # alive again
    age(500)
    assert W.claim(a, 'codex', root=tmp_path)[0] and W.find(W.load(tmp_path), a)['history'][-2]['event'] == 'expired'


def test_lifecycle_done_needs_commit_and_foreign_holder_cannot_change_it(tmp_path):
    import pytest
    a = _add(tmp_path, 'Build')
    W.claim(a, 's1', root=tmp_path)
    with pytest.raises(SystemExit):
        W.update(a, 's2', status='done', commit='abc', root=tmp_path)
    with pytest.raises(SystemExit):
        W.update(a, 's1', status='done', root=tmp_path, require_commit=True)
    t = W.update(a, 's1', status='done', commit='abc1234', jobs=['31522781'], note='ok', require_commit=True, root=tmp_path)
    assert t['status'] == 'done' and t['jobs'] == ['31522781'] and not W.live(t)
    assert W.claim(a, 's2', root=tmp_path)[0] is False
    b = _add(tmp_path, 'Other')
    W.claim(b, 's1', root=tmp_path); assert W.update(b, 's1', status='open', root=tmp_path)['session'] == ''


def test_land_lock(tmp_path):
    assert W.land_check('s1', tmp_path)[0] == 'free'
    assert W.main(['land-lock', 'acquire', '--session', 's1', '--root', str(tmp_path)]) == 0
    assert W.land_check('s1', tmp_path)[0] == 'ours' and W.land_check('s2', tmp_path)[0] == 'held'
    assert W.main(['land-lock', 'acquire', '--session', 's2', '--root', str(tmp_path)]) == 3
    assert W.main(['land-lock', 'check', '--session', 's2', '--root', str(tmp_path)]) == 3
    assert W.main(['land-lock', 'release', '--session', 's2', '--root', str(tmp_path)]) == 3
    assert W.main(['land-lock', 'release', '--session', 's1', '--root', str(tmp_path)]) == 0
    assert W.main(['land-lock', 'acquire', '--session', 's2', '--root', str(tmp_path)]) == 0
    cur = AL.read(W.LAND, tmp_path)
    cur['renewed_at'] = AL.stamp(AL.now() - datetime.timedelta(seconds=7200)); AL.path(W.LAND, tmp_path).write_text(json.dumps(cur))
    assert W.land_check('s1', tmp_path)[0] == 'free'                                                # a crashed lander's lock expires


def _racer(args):
    root, tid, who = args
    return W.claim(tid, who, root=root)[0]


def test_concurrent_claims_have_exactly_one_winner(tmp_path):
    a = _add(tmp_path, 'Contended', 'cmu', 'collect', ['hierarchy/cmu'])
    with mp.get_context('fork').Pool(8) as pool:
        wins = pool.map(_racer, [(tmp_path, a, f's{i}') for i in range(8)])
    assert sum(wins) == 1
    ids = []
    with mp.get_context('fork').Pool(8) as pool:
        ids = pool.map(_adder, [(tmp_path, i) for i in range(16)])
    assert len(W.load(tmp_path)) == 17 and len({t['id'] for t in W.load(tmp_path)}) == 17


def _adder(args):
    root, i = args
    return W.add(f'task number {i}', root=root)[0]


def test_cli_exit_codes_and_import(tmp_path, capsys, monkeypatch):
    r = str(tmp_path)
    monkeypatch.delenv('ATLAS_SESSION', raising=False); monkeypatch.delenv('CLAUDE_SESSION_ID', raising=False)
    import pytest
    with pytest.raises(SystemExit):
        W.main(['add', '--title', 'x', '--root', r])                                                 # no session id: refuse to guess
    assert W.main(['add', '--title', 'First', '--school', 'mit', '--kind', 'collect', '--scope', 'a/b', '--session', 's1', '--root', r]) == 0
    assert W.main(['claim', 'T001', '--session', 's1', '--branch', 'agent/x', '--root', r]) == 0
    assert W.main(['add', '--title', 'Second', '--school', 'mit', '--kind', 'collect', '--session', 's2', '--root', r]) == 0
    assert W.main(['claim', 'T002', '--session', 's2', '--root', r]) == 3
    assert 'agent/x' in capsys.readouterr().err
    assert W.main(['heartbeat', 'T001', '--session', 's1', '--job', '5', '--running', '--root', r]) == 0
    assert W.main(['list', '--root', r, '--kind', 'collect']) == 0 and 'running' in capsys.readouterr().out
    assert W.main(['done', 'T001', '--commit', 'abc', '--session', 's1', '--root', r]) == 0
    seed = tmp_path / 's.json'
    seed.write_text(json.dumps([dict(id='S1', title='Seeded', kind='review', claimed_by='codex-x', branch='agent/y'), dict(id='T001', title='dup id')]))
    assert W.main(['import', str(seed), '--root', r]) == 0 and 'imported 1' in capsys.readouterr().out
    t = W.find(W.load(tmp_path), 'S1')
    assert t['session'] == 'codex-x' and W.live(t)
