"""fulltext-push/core_queued_fill.py (2026-11-17): CORE lookup by DOI for queued non-lab works. Fixture catalog and a fake session:
no network, no key. Checks the query (DOIs only), the link filter, resume, error handling, the plan rows and the guarded write."""
import json
import sqlite3
import time

import pytest

import core_queued_fill as C
import ftp_common as F
import queued_oa_fill as Q
from test_queued_oa_fill import DDL, backup

USABLE = lambda u: 'doi.org' not in u and 'core.ac.uk' not in u  # noqa: E731


class Resp:
    def __init__(self, code=200, results=None, left=None):
        self.status_code, self._r = code, results or []
        self.headers = {} if left is None else {'x-ratelimit-remaining': str(left)}

    def json(self):
        return {'results': self._r}


class Sess:
    def __init__(self, handler):
        self.handler, self.calls = handler, []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return self.handler(params)


def out(doi, *links, dl=None):
    return dict(doi=doi, sourceFulltextUrls=list(links), downloadUrl=dl)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(F, 'FT', tmp_path)
    monkeypatch.setattr(Q.F, 'FT', tmp_path)
    s = tmp_path / 't'
    s.mkdir()
    db = sqlite3.connect(s / 'catalog.sqlite')
    db.executescript(DDL)
    for i, d, st in [('t_a', '10.1/A', 'queued'), ('t_b', 'https://doi.org/10.1/b', 'queued'), ('t_c', None, 'queued'), ('t_d', '10.1/d', 'queued'),
                     ('t_e', '10.1/e', 'downloaded'), ('t_f', '10.48550/arXiv.1', 'queued'), ('t_g', '10.1/q"x', 'queued')]:
        db.execute("INSERT INTO works (id, title, doi, graph_json, status) VALUES (?,?,?,?,?)", (i, 'T', d, '{}', st))
    db.execute("INSERT INTO candidates VALUES ('t_d','https://x.example/d.pdf',NULL,NULL,NULL,'e')")
    db.commit()
    db.close()
    return s


def test_plan_dois_filters(store):
    assert dict(C.plan_dois(['t'])) == {'10.1/a': [('t', 't_a')], '10.1/b': [('t', 't_b')]}


def test_ask_sends_only_dois_and_filters_links():
    def h(p):
        assert set(p) == {'q', 'limit', 'offset'} and p['q'] == 'doi:"10.1/a" OR doi:"10.1/b"'
        return Resp(results=[out('10.1/A', 'https://repo.example.edu/a.pdf', 'https://doi.org/10.1/a', dl='https://core.ac.uk/download/1.pdf'),
                             out('10.9/other', 'https://repo.example.edu/zzz.pdf')])
    s = Sess(h)
    got = C.ask(s, ['10.1/a', '10.1/b'], sleep=lambda x: None, usable=USABLE)
    assert got == {'10.1/a': ['https://repo.example.edu/a.pdf'], '10.1/b': []}


def test_ask_follows_full_pages_and_backs_off():
    waits, state = [], dict(n=0)

    def h(p):
        state['n'] += 1
        if state['n'] == 1:
            return Resp(429)
        if p['offset'] == 0:
            return Resp(results=[out('10.1/a', f'https://r.example/{i}.pdf') for i in range(100)])
        return Resp(results=[out('10.1/b', 'https://r.example/b.pdf')])
    got = C.ask(Sess(h), ['10.1/a', '10.1/b'], sleep=waits.append, usable=USABLE)
    assert 120 in waits and len(got['10.1/a']) == 100 and got['10.1/b'] == ['https://r.example/b.pdf']


def test_ask_gives_up_with_none():
    assert C.ask(Sess(lambda p: Resp(500)), ['10.1/a'], sleep=lambda x: None, usable=USABLE) is None


def test_lookup_resumes_and_skips_cached(store, tmp_path):
    cache = tmp_path / 'c.jsonl'
    s = Sess(lambda p: Resp(results=[out('10.1/a', 'https://r.example/a.pdf')]))
    kw = dict(session=s, sleep=lambda x: None, usable=USABLE, shared={}, log=lambda *a, **k: None)
    n = C.lookup(['t'], cache, **kw)
    assert n['asked'] == 2 and n['with_links'] == 1 and len(s.calls) == 1
    again = C.lookup(['t'], cache, **kw)
    assert again['asked'] == 0 and len(s.calls) == 1
    shared = {'10.1/a': dict(doi='10.1/a', links=[])}
    assert C.lookup(['t'], tmp_path / 'c2.jsonl', **dict(kw, shared=shared))['asked'] == 1   # the shared cache answers 10.1/a


def test_lookup_errors_are_retried_and_three_in_a_row_stop(store, tmp_path, monkeypatch):
    monkeypatch.setattr(C, 'CHUNK', 1)
    cache = tmp_path / 'c.jsonl'
    n = C.lookup(['t'], cache, session=Sess(lambda p: Resp(500)), sleep=lambda x: None, usable=USABLE, shared={}, log=lambda *a, **k: None)
    assert n['errors'] == 2 and 'stopped' not in n            # only two DOIs, each one a failed request
    assert C.lookup(['t'], cache, session=Sess(lambda p: Resp(results=[])), sleep=lambda x: None, usable=USABLE, shared={}, log=lambda *a, **k: None)['asked'] == 2


def test_sample_is_seeded(store, tmp_path):
    kw = dict(session=Sess(lambda p: Resp()), sleep=lambda x: None, usable=USABLE, shared={}, log=lambda *a, **k: None, sample=1, seed=3)
    C.lookup(['t'], tmp_path / 'a.jsonl', **kw)
    C.lookup(['t'], tmp_path / 'b.jsonl', **kw)
    assert (tmp_path / 'a.jsonl').read_text().split('"at"')[0] == (tmp_path / 'b.jsonl').read_text().split('"at"')[0]
    assert len((tmp_path / 'a.jsonl').read_text().splitlines()) == 1


def test_plan_apply_only_candidates_and_idempotent(store, tmp_path):
    cache = tmp_path / 'c.jsonl'
    cache.write_text(json.dumps(dict(doi='10.1/a', links=['https://r.example/a.pdf', 'https://doi.org/10.1/a'])) + '\n' +
                     json.dumps(dict(doi='10.1/b', error=True)) + '\n')
    plan = tmp_path / 'p.json.gz'
    saved = C.build_plan(['t'], cache, plan, shared={}, usable=USABLE)
    assert saved['t']['counts'] == dict(queued=2, asked=1, not_asked=1, works_with_link=1, rows=1)
    backup(tmp_path)
    db = sqlite3.connect(store / 'catalog.sqlite')
    before = [db.execute(f'SELECT * FROM {t} ORDER BY 1').fetchall() for t in ('works', 'attempts')]
    db.close()
    C.main(['apply', 't', '--plan-file', str(plan), '--backup-dir', str(tmp_path), '--lock-wait', '0'])
    db = sqlite3.connect(store / 'catalog.sqlite')
    assert db.execute("SELECT work_id, url FROM candidates WHERE work_id='t_a'").fetchall() == [('t_a', 'https://r.example/a.pdf')]
    assert [db.execute(f'SELECT * FROM {t} ORDER BY 1').fetchall() for t in ('works', 'attempts')] == before
    db.close()
    C.main(['apply', 't', '--plan-file', str(plan), '--backup-dir', str(tmp_path), '--lock-wait', '0'])   # t_a has a candidate now: nothing more
    db = sqlite3.connect(store / 'catalog.sqlite')
    assert db.execute('SELECT count(*) FROM candidates').fetchone()[0] == 2
    db.close()


def test_apply_refuses_without_backup(store, tmp_path):
    plan = tmp_path / 'p.json.gz'
    C.build_plan(['t'], tmp_path / 'none.jsonl', plan, shared={}, usable=USABLE)
    with pytest.raises(SystemExit, match='no catalog-backup'):
        C.main(['apply', 't', '--plan-file', str(plan), '--backup-dir', str(tmp_path)])


def test_max_minutes_stops(store, tmp_path):
    n = C.lookup(['t'], tmp_path / 'c.jsonl', max_minutes=-1, session=Sess(lambda p: Resp()), sleep=lambda x: None, usable=USABLE, shared={}, log=lambda *a, **k: None)
    assert n['stopped'] == 'max-minutes' and n['asked'] == 0
    assert time.monotonic() > 0
