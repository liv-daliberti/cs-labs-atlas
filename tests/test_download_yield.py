"""Download yield (2026-11-03): MIT's DSpace file store is an approved delivery host, a 429 is a shared timed cooldown instead of a
pause for the rest of the pass, the hosts that rate-limit us share one request clock across loops, and the reader's confirmed link
becomes a candidate (channels/reader_link.py)."""
import gzip
import json
import sqlite3
from collections import defaultdict

import importlib.util
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
for d in (CODE / 'fulltext-push', CODE / 'vendor' / 'homogenizing_scripts'):   # this worktree's code before the main checkout's
    if str(d) in sys.path:
        sys.path.remove(str(d))
    sys.path.insert(0, str(d))

import channels as CH  # noqa: E402
import channel_runner as R  # noqa: E402
import host_throttle as HT  # noqa: E402

_spec = importlib.util.spec_from_file_location('wt_collector_wrapper', CODE / 'vendor' / 'cmu_tools' / 'collector_wrapper.py')
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)


def test_reserve_hands_out_slots_across_processes(tmp_path):
    p = tmp_path / 'ht.json'
    assert HT.reserve('dspace.mit.edu', 15, now=1000.0, path=p) == 0.0
    assert HT.reserve('dspace.mit.edu', 15, now=1000.0, path=p) == 15.0     # a second loop at the same moment waits one slot
    assert HT.reserve('dspace.mit.edu', 15, now=1001.0, path=p) == 29.0
    assert HT.reserve('dspace.mit.edu', 15, now=2000.0, path=p) == 0.0      # a quiet host: no wait
    assert HT.reserve('other.example', 3, now=1000.0, path=p) == 0.0        # hosts are independent


def test_429_cooldown_doubles_and_is_capped(tmp_path):
    p = tmp_path / 'ht.json'
    assert HT.cooldown_left('h', now=0, path=p) == 0.0
    assert HT.record_429('h', now=100.0, path=p) == 300.0
    assert HT.cooldown_left('h', now=150.0, path=p) == 250.0
    assert HT.record_429('h', now=200.0, path=p) == 600.0
    assert HT.record_429('h', now=300.0, path=p) == 1200.0
    assert HT.record_429('h', now=400.0, path=p) == 2400.0
    assert HT.record_429('h', now=500.0, path=p) == 3600.0                   # capped
    assert HT.record_429('h', now=500.0 + HT.WINDOW + 4000, path=p) == 300.0 # old 429s are forgotten


def test_a_short_cooldown_is_waited_out_and_the_host_asked_again(tmp_path, monkeypatch):
    monkeypatch.setattr(HT, 'state_path', lambda: tmp_path / 'ht.json')
    slept = []
    now = [1000.0]
    monkeypatch.setattr(W.time, 'sleep', lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)))
    monkeypatch.setattr(HT.time, 'time', lambda: now[0])
    b = W._Blocked()
    assert 'h.example' not in b
    b['h.example'] = W.RATE_429                  # what the collector writes on an HTTP 429
    assert b['h.example'] == W.RATE_429          # the collector reads it back for the failing request's own message
    assert 'h.example' in b or slept             # the next worker waits out the 300 s cooldown ...
    assert slept and 300 <= slept[0] <= 305
    assert 'h.example' not in b                  # ... and then the host is no longer paused


def test_a_long_cooldown_pauses_the_host_until_it_ends(tmp_path, monkeypatch):
    monkeypatch.setattr(HT, 'state_path', lambda: tmp_path / 'ht.json')
    now = [5000.0]
    monkeypatch.setattr(HT.time, 'time', lambda: now[0])
    slept = []
    monkeypatch.setattr(W.time, 'sleep', lambda s: slept.append(s))
    b = W._Blocked()
    for _ in range(3):
        b['h.example'] = W.RATE_429              # a third 429 within two hours: 1,200 s, longer than WAIT_MAX
    assert 'h.example' in b and not slept        # paused as before (the pass's remaining works fail as source_paused)
    now[0] += 1300
    assert 'h.example' not in b


def test_another_process_429_is_honoured(tmp_path, monkeypatch):
    monkeypatch.setattr(HT, 'state_path', lambda: tmp_path / 'ht.json')
    HT.record_429('shared.example')              # a different loop's 429
    for _ in range(2):
        HT.record_429('shared.example')
    b = W._Blocked()
    assert 'shared.example' in b


def test_other_pauses_are_untouched():
    b = W._Blocked()
    b['x.example'] = 'robots policy unavailable; retry later'
    assert 'x.example' in b and 'x.example' in b       # permanent for the pass, as in the collector


def test_mit_file_store_is_a_path_limited_delivery_host(tmp_path):
    PublicClient = W.c.PublicClient
    (tmp_path / 'sources').mkdir()
    c = PublicClient(tmp_path, {'dspace.mit.edu'})
    rules = c.rules['cf003.cdn.4science.cloud']
    ua = 'HomogenizingScienceResearch/0.1'
    assert rules.can_fetch('https://cf003.cdn.4science.cloud/4s-assetstore-prod--mit--dspace/8156667396?response-content-type=application%2Fpdf', ua)
    assert not rules.can_fetch('https://cf003.cdn.4science.cloud/4s-assetstore-prod--someone-else/1', ua)   # no other tenant
    assert 'cf003.cdn.4science.cloud' in W.c.PUBLIC_REDIRECT_HOSTS
    assert 'cf002.cdn.4science.cloud' in W.c.PUBLIC_REDIRECT_HOSTS


def test_requeue_clears_the_mit_store_redirect_and_a_robots_429(tmp_path):
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    db.execute('CREATE TABLE works (id TEXT PRIMARY KEY, status TEXT)')
    db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT)')
    db.execute("INSERT INTO works VALUES ('w1','needs_access_review')")
    db.executemany('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)', [
        ('w1', 'https://dspace.mit.edu/server/api/core/bitstreams/a/content', 't', 'unavailable',
         'Redirect or URL outside the evidence-approved public hosts: cf003.cdn.4science.cloud'),
        ('w1', 'https://dspace.mit.edu/bitstream/1/2/x.pdf', 't', 'unavailable', '429 Client Error: Too Many Requests for url: https://dspace.mit.edu/robots.txt'),
        ('w1', 'https://idp.example.org/x', 't', 'unavailable', 'Redirect or URL outside the evidence-approved public hosts: idp.nature.com')])
    db.commit(); db.close()
    (tmp_path / 'staged').mkdir()
    W.requeue(tmp_path)
    left = [r[0] for r in sqlite3.connect(str(tmp_path / 'catalog.sqlite')).execute('SELECT url FROM attempts')]
    assert left == ['https://idp.example.org/x']        # a login redirect stays a lasting failure


def _release(tmp_path):
    rel = tmp_path / 'rel'
    (rel / 'reader').mkdir(parents=True)
    (rel / 'hierarchy' / 's').mkdir(parents=True)  # route-ok: release layout
    reader = [
        dict(key='a', catalog_work='w_a', decision='link', stored_copy=False, link_basis='openalex_location', source_url='https://repo.example.edu/a.pdf'),
        dict(key='b', catalog_work='w_b', decision='link', stored_copy=False, link_basis='openalex_location', source_url='https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1'),
        dict(key='c', catalog_work='w_c', decision='link', stored_copy=False, link_basis='arxiv_id_doi', source_url='https://doi.org/10.1/x'),
        dict(key='d', catalog_work='w_d', decision='link', stored_copy=False, link_basis='openalex_location', source_url='https://repo.example.edu/d.pdf'),
    ]
    ledger = [dict(key=k, work_id='w_' + k, reason_code=c) for k, c in
              [('a', 'found_awaiting_download'), ('b', 'pending_retry'), ('c', 'found_awaiting_download'), ('d', 'paywall_only')]]
    for name, rows in (('reader/s.jsonl.gz', reader), ('hierarchy/s/unavailable.jsonl.gz', ledger)):  # route-ok: release layout
        with gzip.open(rel / name, 'wt') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in rows))
    return rel


def test_reader_link_channel_adds_the_confirmed_url_of_queued_papers(tmp_path, monkeypatch):
    import priority_file as PF
    import channels.reader_link as RL
    rel = _release(tmp_path)
    monkeypatch.setattr(PF, 'release_dir', lambda release=None: rel)
    RL._CACHE.clear()
    assert 'reader_link' in CH.NAMES and 'reader_link' in CH.NATIVE
    mod = CH.load('reader_link')
    mk = lambda w: CH.Paper(w, w, dict(), set())  # noqa: E731
    ps = [mk('w_a'), mk('w_b'), mk('w_c'), mk('w_d'), mk('w_x')]
    assert [bool(mod.APPLIES('s', p)) for p in ps] == [True, True, True, False, False]   # paywall_only and unknown works are out
    ctx = R.Ctx('s', ps, defaultdict(set), dry=True)
    res = {r.work_id: r for r in mod.discover('s', [p for p in ps if mod.APPLIES('s', p)], ctx)}
    assert res['w_a'].status == 'found' and res['w_a'].urls[0]['url'] == 'https://repo.example.edu/a.pdf'
    assert res['w_a'].urls[0]['source'] == 'reader_link'
    assert res['w_b'].status == 'none'                    # hosts the other channels never use (s2_key_lookup.BAD_HOSTS): not a candidate
    assert res['w_c'].status == 'none'                    # a DOI resolver link lands on the publisher


def _store(tmp_path):
    out = tmp_path / 'store'
    out.mkdir()
    db = sqlite3.connect(str(out / 'catalog.sqlite'))
    db.execute('CREATE TABLE works (id TEXT PRIMARY KEY, status TEXT)')
    db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT)')
    db.executemany('INSERT INTO works VALUES (?,?)', [('w1', 'needs_access_review'), ('w2', 'needs_access_review'), ('w3', 'downloaded'), ('w4', 'needs_access_review')])
    old, new = '2026-11-03T01:00:00+00:00', '2026-11-03T20:00:00+00:00'
    to = "HTTPSConnectionPool(host='x.example', port=443): Read timed out."
    db.executemany('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)', [
        ('w1', 'https://x.example/a.pdf', old, 'unavailable', to),                               # requeued
        ('w1', 'https://x.example/b.pdf', old, 'unavailable', 'robots.txt disallows URL'),       # lasting: stays
        ('w2', 'https://x.example/c.pdf', new, 'unavailable', to),                               # too recent: stays
        ('w3', 'https://x.example/d.pdf', old, 'unavailable', to),                               # already a copy: stays
        ('w4', 'https://www.sciencedirect.com/x', old, 'unavailable', to),                       # publisher host: stays
        ('w4', 'https://y.example/e.pdf', old, 'unavailable', '500 Server Error: Internal Server Error for url: https://y.example/e.pdf')])
    db.commit(); db.close()
    (out / 'staged').mkdir()
    return out


def test_priority_retry_asks_transient_failures_again_at_most_twice(tmp_path):
    from datetime import datetime, timezone
    import priority_retry as PR
    out = _store(tmp_path)
    now = datetime(2026, 11, 3, 21, 0, tzinfo=timezone.utc)
    ids = ['w1', 'w2', 'w3', 'w4']
    assert PR.requeue_transient('s', ids, now=now, store=out, dry=True) == 2
    assert PR.requeue_transient('s', ids, now=now, store=out) == 2
    left = sorted(r[0] for r in sqlite3.connect(str(out / 'catalog.sqlite')).execute('SELECT url FROM attempts'))
    assert left == ['https://www.sciencedirect.com/x', 'https://x.example/b.pdf', 'https://x.example/c.pdf', 'https://x.example/d.pdf']
    log = [json.loads(line) for line in (out / 'staged' / 'requeued-attempts.jsonl').read_text().splitlines()]
    assert sorted(r['url'] for r in log) == ['https://x.example/a.pdf', 'https://y.example/e.pdf'] and log[0]['requeued_by'].endswith('priority_retry.py')
    for _ in range(2):   # the collector asked again and the URL failed the same way, twice more: the third time it is left alone
        db = sqlite3.connect(str(out / 'catalog.sqlite'))
        db.execute("INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES ('w1','https://x.example/a.pdf','2026-11-03T02:00:00+00:00','unavailable','Read timed out.')")
        db.commit(); db.close()
        PR.requeue_transient('s', ids, now=now, store=out)
    assert PR.requeue_transient('s', ids, now=now, store=out) == 0
    assert 'https://x.example/a.pdf' in [r[0] for r in sqlite3.connect(str(out / 'catalog.sqlite')).execute('SELECT url FROM attempts')]
