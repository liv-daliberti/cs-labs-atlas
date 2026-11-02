"""tools/agent_lease.py (ROADMAP #17): a live lease refuses a second session; an expired one is taken over; renew and release respect the holder."""
import datetime

import agent_lease as L


def test_second_session_is_refused_while_the_lease_is_live(tmp_path):
    ok, a = L.acquire('lab-page', 's1', ttl=600, root=tmp_path)
    assert ok and a['session'] == 's1'
    ok, held = L.acquire('lab-page', 's2', root=tmp_path)
    assert not ok and held['session'] == 's1'
    assert L.acquire('lab-page', 's1', root=tmp_path)[0]                       # the holder may acquire again (a restart of the same session)
    assert L.renew('lab-page', 's2', root=tmp_path)[0] is False and L.release('lab-page', 's2', root=tmp_path)[0] is False
    assert L.renew('lab-page', 's1', note='step 3', root=tmp_path)[1]['note'] == 'step 3'
    assert L.release('lab-page', 's1', root=tmp_path)[0] and L.acquire('lab-page', 's2', root=tmp_path)[0]


def test_an_expired_lease_is_free_and_force_overrides(tmp_path):
    L.acquire('dl', 's1', ttl=60, root=tmp_path)
    old = L.read('dl', tmp_path)
    old['renewed_at'] = L.stamp(L.now() - datetime.timedelta(seconds=3600))
    L.path('dl', tmp_path).write_text(__import__('json').dumps(old))
    assert not L.live(L.read('dl', tmp_path)) and L.acquire('dl', 's2', root=tmp_path)[0]
    assert not L.acquire('dl', 's3', root=tmp_path)[0] and L.acquire('dl', 's3', root=tmp_path, force=True)[0]


def test_status_and_cli_exit_codes(tmp_path, capsys):
    L.acquire('a', 's1', root=tmp_path)
    assert L.main(['status', '--root', str(tmp_path)]) == 0 and 'LIVE' in capsys.readouterr().out
    assert L.main(['acquire', 'a', '--session', 's2', '--root', str(tmp_path)]) == 3
    assert L.main(['check', 'a', '--session', 's1', '--root', str(tmp_path)]) == 0 and L.main(['check', 'a', '--session', 's2', '--root', str(tmp_path)]) == 3
    assert L.main(['check', 'nobody', '--session', 's2', '--root', str(tmp_path)]) == 0
