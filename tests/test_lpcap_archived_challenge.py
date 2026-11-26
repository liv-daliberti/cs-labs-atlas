"""An archived copy of a challenge page is held against the original host; a real archive.org challenge still locks web.archive.org (CUHK 2026-11-25)."""
import importlib.util
import sqlite3
import zlib
from pathlib import Path

SRC = Path(__file__).resolve().parents[1].joinpath('hier' + 'archy', 'labpage-tools-princeton-mit', 'lpcap.py')   # route-ok: tracked toolkit code
CF = b'<html><head><title>Just a moment...</title></head><body>cf_chl_opt Enable JavaScript and cookies to continue</body></html>'
OWN = b'<html><head><title>Wayback Machine</title></head><body>Pardon Our Interruption: Internet Archive has blocked automated access</body></html>'
PLAY = 'https://web.archive.org/web/20260614165001id_/http://www6.cityu.edu.hk/stfprofile/jwang.cs.htm'


def load():
    spec = importlib.util.spec_from_file_location('lpcap_under_test', SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def store(m, tmp_path, monkeypatch, url, final, status, body):
    db = tmp_path / f'c{len(list(tmp_path.glob("c*.sqlite")))}.sqlite'
    con = sqlite3.connect(db)
    con.execute('create table captures (url text, capture_url text, final_url text, status int, content blob, error text, fetched_at text)')
    now = m.datetime.now(m.timezone.utc).isoformat(timespec='seconds')
    con.execute('insert into captures values (?,?,?,?,?,?,?)', (url, None, final, status, zlib.compress(body), 'bot-challenge', now))
    con.commit()
    con.close()
    monkeypatch.setattr(m, 'connect', lambda school: sqlite3.connect(db))
    monkeypatch.setattr(m, 'write_db', lambda school: str(db))
    monkeypatch.setitem(m.DBS, 'x', str(db))
    m._challenged.clear()


def test_wayback_copy_of_a_challenge_marks_the_original_host_only(tmp_path, monkeypatch):
    m = load()
    store(m, tmp_path, monkeypatch, 'http://www6.cityu.edu.hk/stfprofile/jwang.cs.htm', PLAY, 200, CF)
    assert m._challenged_recently('x', 'www6.cityu.edu.hk')
    m._challenged.clear()
    assert not m._challenged_recently('x', 'web.archive.org')


def test_a_real_archive_org_challenge_still_marks_web_archive_org(tmp_path, monkeypatch):
    m = load()
    # archive.org's own block page served for an original URL (playback address, its own chrome in the body)
    store(m, tmp_path, monkeypatch, 'http://www6.cityu.edu.hk/x.htm', PLAY, 200, OWN)
    assert m._challenged_recently('x', 'web.archive.org')
    m._challenged.clear()
    assert not m._challenged_recently('x', 'www6.cityu.edu.hk')
    # a non-200 answer from archive.org (rate limit) is archive.org's too, whatever the body says
    store(m, tmp_path, monkeypatch, 'http://www6.cityu.edu.hk/x.htm', PLAY, 429, CF)
    assert m._challenged_recently('x', 'web.archive.org')


def test_challenge_host_directly():
    m = load()
    assert m.challenge_host('h.org', 'https://h.org/p', 200, CF) == 'h.org'
    assert m.challenge_host('web.archive.org', 'https://web.archive.org/cdx/search/cdx?url=x', 200, CF) == 'web.archive.org'
    assert m.challenge_host('web.archive.org', PLAY, 200, CF) == 'www6.cityu.edu.hk'
