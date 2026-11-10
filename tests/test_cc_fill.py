"""cc_fill: refused while robots disallow; fills a nocapture slot-half with provenance when allowed (fake network)."""
import json
import sqlite3
import types

import pytest

import cc
import cc_fill
import plan_fetch as PF
from test_cc import fake, warc_record, HTML  # noqa: F401  (fixtures below reuse the no-sleep autouse)

SLOT = {'slot': 'CS', 'dept': 'CS', 'urls': [('https://x.edu/people', '20160101', '20261231')]}


@pytest.fixture(autouse=True)
def nosleep(monkeypatch):
    monkeypatch.setattr(cc.time, 'sleep', lambda s: None)
    cc._last[0] = 0.0


def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cc_fill, 'approval_marker', lambda: str(tmp_path / 'OWNER-APPROVED'))
    (tmp_path / 'OWNER-APPROVED').write_text('approved in test')
    monkeypatch.setattr(PF, 'load', lambda school: (types.SimpleNamespace(SLOTS=[SLOT]), []))
    monkeypatch.setattr(PF, 'slot_usable', lambda con, cap, s, b, st, pis, school: (st == 200, None if st == 200 else 'x'))
    db = str(tmp_path / 'c.sqlite')
    con = cc_fill.open_db(db)
    for y in PF.YEARS:
        for h in ('H1', 'H2'):
            con.execute('insert into plan values(?,?,?,?,?,?,?,?,?,?)', ('CS', 'CS', y, h, None, None, None, 'nocapture', 'none', '[]'))
    con.commit()
    return db


def test_refused_asks_nothing_else(monkeypatch, tmp_path):
    db = setup(monkeypatch, tmp_path)
    h = fake({cc.INDEX + '/robots.txt': (200, {}, b'User-agent: *\nDisallow: /\n'), cc.DATA + '/robots.txt': (200, {}, b'User-agent: *\nDisallow: /\n')})
    assert cc_fill.run('harvard', db, [], None, False, False, http=h) == 4
    assert all('robots.txt' in u for u, _ in h.calls)


def test_fills_with_provenance_and_closes_h2(monkeypatch, tmp_path):
    db = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(PF, 'ONE_CAPTURE_PER_YEAR', {'harvard'})
    line = json.dumps(dict(url='https://x.edu/people', timestamp='20190401000000', filename='crawl-data/a.warc.gz', offset='10', length='99', digest='D'))
    h = fake({cc.INDEX + '/robots.txt': (200, {}, b'User-agent: *\nAllow: /\n'), cc.DATA + '/robots.txt': (404, {}, b''),
              cc.INDEX + '/collinfo.json': (200, {}, json.dumps([{'id': 'CC-MAIN-2019-13'}]).encode()),
              cc.INDEX + '/CC-MAIN-2019-13-index': (200, {}, line.encode()), 'https://x.edu/robots.txt': (404, {}, b''),
              cc.DATA + '/crawl-data/a.warc.gz': (206, {}, warc_record())})
    assert cc_fill.run('harvard', db, [], None, False, False, http=h) == 0
    con = sqlite3.connect(db)
    r = con.execute("select status, capture_url, wayback_timestamp from plan where year=2019 and half='H1'").fetchone()
    assert r == ('ok', 'commoncrawl:crawl-data/a.warc.gz:10:99', '20190401000000')
    assert con.execute("select status from plan where year=2019 and half='H2'").fetchone()[0] == 'out_of_scope'
    assert json.loads(con.execute('select note from captures').fetchone()[0])['crawl'] == 'CC-MAIN-2019-13'
    assert con.execute("select count(*) from plan where status='ok'").fetchone()[0] == 1


def test_no_marker_means_no_request(monkeypatch, tmp_path):
    db = setup(monkeypatch, tmp_path)
    (tmp_path / 'OWNER-APPROVED').unlink()
    h = fake({})
    assert cc_fill.run('harvard', db, [], None, False, False, http=h) == 5
    assert h.calls == []
