"""fulltext-push/pubmed_pmc.py and hdl_requeue.py, and the Handle robots seed in collector_wrapper (2026-11-17). Fixture catalogs and fake sessions only."""
import json
import sqlite3
import types

import pytest

import ftp_common as F
import hdl_requeue as H
import pubmed_pmc as PM
import collector_wrapper as W

DDL = """
CREATE TABLE works (id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER, graph_json TEXT NOT NULL DEFAULT '{}', oa_json TEXT, metadata_source TEXT,
  status TEXT NOT NULL DEFAULT 'queued', file_path TEXT, sha256 TEXT, byte_count INTEGER, pages INTEGER, download_url TEXT, downloaded_at TEXT, identity_check TEXT);
CREATE TABLE candidates (work_id TEXT, url TEXT, landing_url TEXT, license TEXT, version TEXT, metadata_source TEXT, PRIMARY KEY(work_id,url));
CREATE TABLE attempts (id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT, status TEXT, detail TEXT);
"""


def make(path, works, cands=(), attempts=()):
    db = sqlite3.connect(str(path))
    db.executescript(DDL)
    db.executemany('INSERT INTO works (id, doi, status) VALUES (?,?,?)', works)
    db.executemany('INSERT INTO candidates (work_id, url) VALUES (?,?)', cands)
    db.executemany('INSERT INTO attempts (work_id, url, status, detail) VALUES (?,?,?,?)', attempts)
    db.commit()
    db.close()


def test_pubmed_works_selects_non_local_pubmed_landings_without_a_pmc_candidate(tmp_path):
    make(tmp_path / 'c.sqlite', [('a', '10.1/a', 'needs_access_review'), ('b', None, 'queued'), ('c', None, 'downloaded'), ('d', None, 'queued'), ('e', None, 'queued')],
         [('a', 'https://pubmed.ncbi.nlm.nih.gov/111/'), ('b', 'https://pubmed.ncbi.nlm.nih.gov/222'), ('c', 'https://pubmed.ncbi.nlm.nih.gov/333/'),
          ('d', 'https://pubmed.ncbi.nlm.nih.gov/444/'), ('d', 'https://pmc-oa-opendata.s3.amazonaws.com/PMC1.1/PMC1.1.pdf'), ('e', 'https://pubmed.ncbi.nlm.nih.gov/?term=x')])
    assert PM.pubmed_works('t', path=tmp_path / 'c.sqlite') == [('a', '111', '10.1/a'), ('b', '222', None)]


def test_idconv_batches_caches_and_stops_on_a_hard_error():
    calls = []

    class R:
        def __init__(self, code, js=None):
            self.status_code, self._js = code, js
        def json(self):
            return self._js

    class S:
        def get(self, url, params, timeout):
            calls.append(params['ids'].split(','))
            return R(200, dict(records=[dict(pmid=p, pmcid='PMC' + p + '9') if p != '3' else dict(pmid=p, status='error', errmsg='x') for p in params['ids'].split(',')]))

    cache = {}
    PM.idconv(S(), ['1', '2', '3'], cache, delay=0)
    assert cache == {'1': '19', '2': '29', '3': ''}
    PM.idconv(S(), ['1', '2', '4'], cache, delay=0)
    assert calls[-1] == ['4'] and len(calls) == 2

    class Bad:
        def get(self, url, params, timeout):
            return R(404)
    with pytest.raises(RuntimeError):
        PM.idconv(Bad(), ['9'], {}, delay=0)


def test_plan_rows_only_for_pmcids_in_the_open_data_bucket(monkeypatch):
    import s2_key_lookup as s2k
    monkeypatch.setattr(s2k, 'pmc_files', lambda s, p, memo: ['https://b/PMC%s.1/PMC%s.1.pdf' % (p, p)] if p == '19' else [])
    rows, n = PM.plan_rows([('a', '1', None), ('b', '2', None), ('c', '3', None)], {'1': '19', '2': '29', '3': ''}, None)
    assert [r['work_id'] for r in rows] == ['a'] and rows[0]['source'] == 'pubmed_pmc_open_data' and rows[0]['detail'] == '1:PMC19'
    assert (n['no_pmcid'], n['not_in_open_data'], n['works_with_files']) == (1, 1, 1)


def test_hdl_stale_classes():
    ok = lambda o, t: t == 'repo.example.edu'  # noqa: E731
    row = lambda d: dict(detail=d)  # noqa: E731
    assert H.stale_class(row('Redirect or URL outside the evidence-approved public hosts: repo.example.edu'), ok) == 'unapproved_redirect'
    assert H.stale_class(row('Redirect or URL outside the evidence-approved public hosts: www.tandfonline.com'), ok) is None
    assert H.stale_class(row('405 Client Error: Not Allowed for url: https://dr.ntu.edu.sg/robots.txt'), ok) == 'robots_error'
    assert H.stale_class(row('403 Client Error: Forbidden for url: https://x.org/robots.txt'), ok) is None
    assert H.stale_class(row('429 Client Error: Too Many Requests for url: https://x.org/robots.txt'), ok) is None
    assert H.stale_class(row('source_paused: HTTP 429; retry later per server guidance'), ok) is None
    assert H.stale_class(row('robots.txt disallows URL'), ok) is None


def test_hdl_requeue_plan_and_apply_touch_only_the_stale_pairs(tmp_path, monkeypatch):
    import queued_oa_fill as Q
    monkeypatch.setattr(F, 'FT', tmp_path)
    (tmp_path / 's').mkdir()
    out = 'Redirect or URL outside the evidence-approved public hosts: '
    make(tmp_path / 's' / 'catalog.sqlite', [('a', None, 'needs_access_review'), ('b', None, 'needs_access_review'), ('c', None, 'needs_access_review'), ('d', None, 'downloaded')],
         attempts=[('a', 'https://hdl.handle.net/1/a', 'unavailable', out + 'repo.example.edu'),
                   ('b', 'https://hdl.handle.net/1/b', 'unavailable', out + 'www.tandfonline.com'),
                   ('c', 'https://hdl.handle.net/1/c', 'unavailable', out + 'repo.example.edu'),
                   ('c', 'https://hdl.handle.net/1/c', 'unavailable', 'robots.txt disallows URL'),
                   ('d', 'https://hdl.handle.net/1/d', 'unavailable', out + 'repo.example.edu'),
                   ('a', 'https://other.example/x.pdf', 'unavailable', 'Response is not a PDF')])
    plan, n = H.plan_school('s', redirect_ok=lambda o, t: t == 'repo.example.edu')
    assert list(plan) == ['a'] and n['works'] == 1 and n['pairs_unapproved_redirect'] == 1
    monkeypatch.setattr(Q, 'check_backup', lambda s, d: None)
    monkeypatch.setattr(Q, 'check_no_writer', lambda s, w=0, p=2: None)
    monkeypatch.setattr(Q, 'integrity_ok', lambda s: True)
    res = H.apply_school('s', plan, 'bk', lock_wait=0)
    assert res['requeued_works'] == 1 and res['attempts_removed'] == 1 and res['integrity']
    db = sqlite3.connect(str(tmp_path / 's' / 'catalog.sqlite'))
    assert db.execute("SELECT status FROM works WHERE id='a'").fetchone()[0] == 'queued'
    assert db.execute("SELECT count(*) FROM attempts").fetchone()[0] == 5  # only a's hdl attempt went; its other URL stays
    assert db.execute("SELECT status FROM works WHERE id='b'").fetchone()[0] == 'needs_access_review'
    rec = json.loads((tmp_path / 's' / 'staged' / 'requeued-attempts.jsonl').read_text().splitlines()[0])
    assert rec['requeued_by'] == H.TAG and rec['work_id'] == 'a'
    plan2, _ = H.plan_school('s', redirect_ok=lambda o, t: t == 'repo.example.edu')
    assert plan2 == {}  # once per tag


class FakeClient:
    def __init__(self, tmp_path, answer):
        self.rules, self.blocked, self.out, self.answer = {}, {}, tmp_path, answer
        self.paused = []
        self.requests = []

    def get_lock(self, host):
        import threading
        return threading.Lock(), host

    def pause(self, key, delay):
        self.paused.append((key, delay))

    def session(self):
        return self

    def get(self, url, timeout, allow_redirects):
        assert allow_redirects is False and url.endswith('/robots.txt')
        self.requests.append(url)
        if isinstance(self.answer, Exception):
            raise self.answer
        return types.SimpleNamespace(status_code=self.answer[0], text=self.answer[1])


@pytest.mark.parametrize('code,text,seeded,allowed', [
    (405, 'Method not allowed', True, True),        # an error page: no rules
    (404, '', True, True),
    (200, 'User-agent: *\nDisallow: /private/\n', True, False),
    (200, 'User-agent: ClaudeBot\nDisallow: /\n', True, False),  # the AI groups bind
    (403, '', False, None), (429, '', False, None), (503, '', False, None), (302, '', False, None),
])
def test_handle_robots_seed(tmp_path, code, text, seeded, allowed):
    cl = FakeClient(tmp_path, (code, text))
    W.seed_handle_robots(cl, 'repo.example.edu')
    assert ('repo.example.edu' in cl.rules) is seeded
    if seeded:
        url = 'https://repo.example.edu/private/x.pdf' if 'private' in text else 'https://repo.example.edu/bitstream/x.pdf'
        assert cl.rules['repo.example.edu'].can_fetch(url, 'HomogenizingScienceResearch/0.2') is allowed
    W.seed_handle_robots(cl, 'repo.example.edu')
    assert len(cl.requests) == (1 if seeded else 2)  # a seeded host is not asked again


def test_handle_robots_seed_leaves_network_errors_to_the_collector(tmp_path):
    import requests
    cl = FakeClient(tmp_path, requests.ConnectionError('x'))
    W.seed_handle_robots(cl, 'repo.example.edu')
    assert cl.rules == {}


def test_a_handle_redirect_to_a_publisher_stays_unapproved():
    assert W.redirect_ok('hdl.handle.net', 'repo.example.edu') and not W.redirect_ok('hdl.handle.net', 'www.tandfonline.com')
    assert not W.redirect_ok('hdl.handle.net', 'idp.example.edu')


def test_a_pubmed_landing_location_is_no_candidate():
    loc = lambda land: dict(landing_page_url=land, is_oa=True, source=dict(type='repository', display_name='PubMed'))  # noqa: E731
    rows, pmc = F.oa_location_rows('w', dict(locations=[loc('https://pubmed.ncbi.nlm.nih.gov/123/')]))
    assert rows == [] and pmc == set()
    rows, _ = F.oa_location_rows('w', dict(locations=[loc('https://repo.example.edu/handle/1/2')]))
    assert [r['url'] for r in rows] == ['https://repo.example.edu/handle/1/2']
