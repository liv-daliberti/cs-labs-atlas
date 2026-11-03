"""A host that refuses every request is recorded without being asked (Wiley), and a source pause is cleared by the pass-start requeue."""
import sqlite3
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
import collector_wrapper as W  # noqa: E402
import review_access as R  # noqa: E402


def test_a_blocked_host_is_refused_before_any_request():
    try:
        W.get(object(), 'https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/x')
    except ValueError as e:
        msg = str(e)
    assert msg.startswith('host_blocked: onlinelibrary.wiley.com ')
    assert not msg.startswith('source_paused:')  # the pass-start requeue must not clear it


def test_review_access_reads_the_block_and_old_wiley_403s_as_a_challenge():
    row = lambda detail, url='https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/x': dict(detail=detail, status='unavailable', url=url)  # noqa: E731
    assert R.cause(row('host_blocked: onlinelibrary.wiley.com answers HTTP 403 (a bot challenge) to every automated request')) == ('challenge', False)
    assert R.cause(row('403 Client Error: Forbidden for url: https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/x')) == ('challenge', False)
    other = 'https://example.org/x.pdf'
    assert R.cause(row('403 Client Error: Forbidden for url: ' + other, other))[0] == 'paywall_or_forbidden'


def test_the_pass_start_requeue_clears_source_paused_but_not_a_host_block(tmp_path):
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    db.execute('CREATE TABLE works (id TEXT PRIMARY KEY, status TEXT)')
    db.execute('CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT)')
    db.executemany('INSERT INTO works VALUES (?,?)', [('w1', 'needs_access_review'), ('w2', 'needs_access_review'), ('w3', 'downloaded')])
    db.executemany('INSERT INTO attempts(work_id,url,observed_at,status,detail) VALUES (?,?,?,?,?)', [
        ('w1', 'https://a.example/1', 't', 'unavailable', 'source_paused: HTTP 429; retry later per server guidance'),
        ('w1', 'https://a.example/2', 't', 'unavailable', 'source_paused: Repeated access or network failures'),
        ('w2', 'https://onlinelibrary.wiley.com/x', 't', 'unavailable', 'host_blocked: onlinelibrary.wiley.com answers HTTP 403'),
        ('w3', 'https://a.example/3', 't', 'unavailable', 'source_paused: HTTP 429; retry later per server guidance')])
    db.commit(); db.close()
    (tmp_path / 'staged').mkdir()
    W.requeue(tmp_path)
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    left = sorted(r[0] for r in db.execute('SELECT url FROM attempts'))
    assert left == ['https://a.example/3', 'https://onlinelibrary.wiley.com/x']  # w1's two pauses are gone; the block and a downloaded work's row stay
    assert len((tmp_path / 'staged' / 'requeued-attempts.jsonl').read_text().splitlines()) == 2
