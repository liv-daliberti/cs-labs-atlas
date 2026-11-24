"""Institutional-repository harvest (fulltext-push/oai_repo.py) and the oai_repo channel (channels/oai_repo.py), on fixture OAI-PMH
responses: parsing (oai_dc, oai_openaire), resumption tokens and resumability, pacing, refusals, robots.txt (AI agents included), the
three match rules with their author check, candidate rows, and the charter verdicts."""
import json
import types
from collections import Counter, defaultdict

import pytest

import channels as CH
import oai_repo as O
from channels import oai_repo as CHN

NS = ('xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" '
      'xmlns:dc="http://purl.org/dc/elements/1.1/"')


def dc_record(i, title, creators, ids, year='2020', status='', relation=None, sets=('col_1',)):
    cs = ''.join(f'<dc:creator>{c}</dc:creator>' for c in creators)
    idn = ''.join(f'<dc:identifier>{x}</dc:identifier>' for x in ids)
    rel = f'<dc:relation>{relation}</dc:relation>' if relation else ''
    st = f' status="{status}"' if status else ''
    ss = ''.join(f'<setSpec>{s}</setSpec>' for s in sets)
    md = '' if status == 'deleted' else (f'<metadata><oai_dc:dc>{cs}<dc:title>{title}</dc:title><dc:date>{year}-05-01</dc:date>{idn}{rel}'
                                          f'<dc:type>article</dc:type></oai_dc:dc></metadata>')
    return f'<record><header{st}><identifier>oai:repo.example.edu:{i}</identifier><datestamp>2026-01-0{i % 9 + 1}T00:00:00Z</datestamp>{ss}</header>{md}</record>'


def page(records, token='', total=None):
    t = f'<resumptionToken completeListSize="{total or 0}">{token}</resumptionToken>' if token else ''
    return f'<?xml version="1.0"?><OAI-PMH {NS}><ListRecords>{"".join(records)}{t}</ListRecords></OAI-PMH>'.encode()


class Resp:
    def __init__(self, content=b'', status=200, headers=None):
        self.content, self.status_code, self.headers = content, status, headers or {}
        self.text = content.decode('utf8', 'ignore')

    def json(self):
        return json.loads(self.content)


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls, self.headers = list(responses), [], {}

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params or {}))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class Clock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s

    def now(self):
        return self.t


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(O, 'db_path', lambda school: tmp_path / f'{school}.sqlite')
    return tmp_path


def client(responses):
    ck = Clock()
    return O.Client(10.0, session=FakeSession(responses), sleep=ck.sleep, clock=ck.now), ck


CONF = dict(verdict='harvest', base='https://repo.example.edu/oai', prefix='oai_dc', sets=['col_1'], landing='https://repo.example.edu/handle/{id}')


def test_parse_dc_record_keeps_relation_dois_apart():
    recs, tok, total, err = O.parse_page(page([dc_record(1, 'Paper One', ['Lovelace, Ada', 'Babbage, Charles'],
                                                         ['https://doi.org/10.1145/ABC.1', 'oai:repo.example.edu:1', 'https://hdl.handle.net/1721.1/12345'],
                                                         relation='https://doi.org/10.9999/other')], 'TOK&amp;1', 7))
    p = O.parse_record(recs[0], CONF['landing'])
    assert (tok, total, err) == ('TOK&1', '7', None)
    assert p['dois'] == ['10.1145/abc.1'] and p['relations'] == ['10.9999/other']
    assert 'https://hdl.handle.net/1721.1/12345' in p['links'] and p['landing'] == 'https://repo.example.edu/handle/1'
    assert p['year'] == 2020 and p['creators'] == ['Lovelace, Ada', 'Babbage, Charles'] and p['sets'] == ['col_1']


def test_mit_style_relation_doi_and_orcid_identifier():
    rec = O.parse_page(page([dc_record(9, 'Paper Nine', ['A, B'], ['https://orcid.org/0000-0002-8220-4108', 'http://hdl.handle.net/1721.1/113087'],
                                       relation='https://doi.org/10.1234/ver')]))[0][0]
    own = O.parse_record(rec, None, None, True)
    assert own['dois'] == ['10.1234/ver'] and own['links'] == ['http://hdl.handle.net/1721.1/113087']
    assert O.parse_record(rec)['dois'] == []


def test_parse_openaire_record_files():
    xml = (f'<OAI-PMH {NS}><ListRecords><record><header><identifier>oai:x:5</identifier><datestamp>2026-01-01T00:00:00Z</datestamp></header>'
           '<metadata><resource xmlns="http://namespace.openaire.eu/schema/oaire/" xmlns:datacite="http://datacite.org/schema/kernel-4">'
           '<datacite:identifier identifierType="Handle">20.500.14299/168520</datacite:identifier>'
           '<datacite:creators><datacite:creator><datacite:creatorName>Hopper, Grace</datacite:creatorName></datacite:creator></datacite:creators>'
           '<datacite:titles><datacite:title>Compilers</datacite:title></datacite:titles>'
           '<datacite:dates><datacite:date dateType="Issued">2019-04-08</datacite:date></datacite:dates>'
           '<datacite:alternateIdentifiers><datacite:alternateIdentifier alternateIdentifierType="doi">10.1234/x</datacite:alternateIdentifier></datacite:alternateIdentifiers>'
           '<file accessRightsURI="http://purl.org/coar/access_right/c_abf2" mimeType="application/pdf" objectType="fulltext">https://repo.example.edu/bitstreams/1/download</file>'
           '</resource></metadata></record></ListRecords></OAI-PMH>')
    recs, *_ = O.parse_page(xml)
    p = O.parse_record(recs[0])
    assert p['title'] == 'Compilers' and p['year'] == 2019 and p['dois'] == ['10.1234/x']
    assert p['links'] == ['https://hdl.handle.net/20.500.14299/168520']
    assert p['files'][0]['url'].endswith('/download') and p['files'][0]['kind'] == 'fulltext'


def test_deleted_and_error_pages():
    recs, *_ = O.parse_page(page([dc_record(2, 'x', [], [], status='deleted')]))
    assert O.parse_record(recs[0])['deleted'] == 1
    assert O.parse_page(f'<OAI-PMH {NS}><error code="noRecordsMatch">none</error></OAI-PMH>')[3] == 'noRecordsMatch'


def test_harvest_follows_tokens_resumes_and_is_incremental(store):
    r1 = Resp(page([dc_record(1, 'Paper One', ['A, B'], ['https://doi.org/10.1/1'])], 'T1', 2))
    r2 = Resp(page([dc_record(2, 'Paper Two', ['A, B'], ['https://doi.org/10.1/2'])]))
    cl, ck = client([r1, r2])
    out = []
    st = O.harvest_oai('s', CONF, cl, out=out.append)
    assert st['records'] == 2 and st['complete_sets'] == 1
    assert cl.s.calls[0] == dict(verb='ListRecords', metadataPrefix='oai_dc', set='col_1')
    assert cl.s.calls[1] == dict(verb='ListRecords', resumptionToken='T1')
    assert ck.sleeps[1] >= 10  # at least the declared delay between the two requests
    # a second run asks only for what changed since the first started, and records a deletion
    cl2, _ = client([Resp(page([dc_record(2, 'Paper Two', [], [], status='deleted')]))])
    O.harvest_oai('s', CONF, cl2, out=out.append)
    assert 'from' in cl2.s.calls[0] and cl2.s.calls[0]['set'] == 'col_1'
    assert O.stats('s')['live'] == 1


def test_harvest_resumes_from_the_stored_token(store):
    cl, _ = client([Resp(page([dc_record(1, 'Paper One', ['A, B'], [])], 'T1', 2)), Resp(b'', 403)])
    with pytest.raises(O.Blocked):
        O.harvest_oai('s', CONF, cl, out=lambda *_: None)
    assert O.stats('s')['records'] == 1
    cl2, _ = client([Resp(page([dc_record(2, 'Paper Two', ['A, B'], [])]))])
    O.harvest_oai('s', CONF, cl2, out=lambda *_: None)
    assert cl2.s.calls[0] == dict(verb='ListRecords', resumptionToken='T1') and O.stats('s')['records'] == 2


@pytest.mark.parametrize('resp', [Resp(b'', 403), Resp(b'', 202), Resp(b'<html>challenge</html>'),
                                  Resp(f'<OAI-PMH {NS}><error code="badArgument">x</error></OAI-PMH>'.encode())])
def test_refusals_stop_the_harvest(store, resp):
    cl, _ = client([resp])
    with pytest.raises(O.Blocked):
        O.harvest_oai('s', CONF, cl, out=lambda *_: None)


def test_retry_after_is_honoured(store):
    cl, ck = client([Resp(b'', 429, {'Retry-After': '30'}), Resp(page([dc_record(1, 'Paper One', ['A, B'], [])]))])
    O.harvest_oai('s', CONF, cl, out=lambda *_: None)
    assert 30 in ck.sleeps and O.stats('s')['records'] == 1


def test_robots_verdicts_include_ai_agents():
    def get(text, status=200):
        return lambda u: types.SimpleNamespace(status_code=status, text=text)
    base = 'https://repo.example.edu/server/oai/request'
    assert O.robots_verdict(base, get('User-agent: *\nDisallow: /search\nCrawl-delay: 10\n'))['crawl_delay'] == 10
    assert O.robots_verdict(base, get('User-agent: *\nDisallow: /search\n'))['allowed']
    v = O.robots_verdict(base, get('User-agent: *\nDisallow: /search\n\nUser-agent: ClaudeBot\nDisallow: /\n'))
    assert not v['allowed'] and v['per_agent']['ClaudeBot'] is False
    assert not O.robots_verdict(base, get('User-agent: anthropic-ai\nDisallow: /server\n'))['allowed']
    assert not O.robots_verdict(base, get('User-agent: *\nDisallow: /server/oai/*\n'))['allowed']   # GaTech's rule
    assert O.robots_verdict(base, get('', 404))['allowed']
    assert not O.robots_verdict(base, get('', 403))['allowed']


def test_harvest_refuses_when_robots_disallow(store, monkeypatch):
    monkeypatch.setattr(O, 'cfg', lambda school: dict(CONF))
    monkeypatch.setattr(O, 'robots_verdict', lambda base: dict(allowed=False, per_agent={}, crawl_delay=None, status=200))
    out = []
    assert O.harvest('s', out=out.append, client=object()) is None and 'robots.txt disallows' in out[-1]
    monkeypatch.setattr(O, 'cfg', lambda school: dict(verdict='skip', reason='no endpoint'))
    out.clear()
    assert O.harvest('s', out=out.append) is None and 'no endpoint' in out[0]


def seeded(store, records):
    c = O.connect('s')
    O.store_records(c, [O.parse_record(x, CONF['landing']) for x in O.parse_page(page(records))[0]], 'col_1')
    c.commit()


def P(key, title, doi=None, year=2020, byline=('Ada Lovelace', 'Charles Babbage'), pis=('Ada Lovelace',), known=()):
    r = dict(work=key, oa=None, doi=doi, title=title, year=year, byline=list(byline), pis=list(pis), editions=[])
    return CH.Paper(key, key, r, set(known))


LONG = 'Analytical Engines and the Mechanical Computation of Bernoulli Numbers'


def test_match_rules(store):
    seeded(store, [
        dc_record(1, LONG, ['Lovelace, Ada', 'Babbage, Charles'], ['https://doi.org/10.1145/abc']),
        dc_record(2, 'A Totally Different Record About Looms and Punched Cards', ['Jacquard, Joseph'], ['https://hdl.handle.net/1721.1/777']),
        dc_record(3, 'Notes on the Difference Engine and its Tabulation Of Polynomials', ['Lovelace, Ada', 'Babbage, Charles'], [], year='2020'),
        dc_record(4, 'Notes on the Difference Engine and its Tabulation Of Polynomials', ['Smith, John', 'Jones, Mary'], [], year='2020'),
        dc_record(5, 'Deleted Record That Used To Hold The Analytical Engine Paper', ['Lovelace, Ada'], ['https://doi.org/10.1234/del'], status='deleted'),
        dc_record(6, 'Short', ['Lovelace, Ada'], []),
        dc_record(7, 'A Paper That Only Relates To Another One By Doi Reference', ['Lovelace, Ada'], [], relation='https://doi.org/10.5555/rel'),
    ])
    idx = CHN.load_index('s')
    rec, how = CHN.match_paper(P('a', 'Different Title Entirely', doi='https://doi.org/10.1145/ABC'), idx)
    assert how == 'doi' and rec['oai_id'].endswith(':1')
    rec, how = CHN.match_paper(P('b', 'Unrelated Words In The Title Here Not Equal', known=['https://hdl.handle.net/1721.1/777']), idx)
    assert how == 'link' and rec['oai_id'].endswith(':2')
    rec, how = CHN.match_paper(P('b2', 'Unrelated Words In The Title Here Not Equal', known=['http://repo.example.edu/handle/2']), idx)
    assert how == 'link' and rec['oai_id'].endswith(':2')
    # title + authors: the record by the same authors wins over the namesake with other authors
    rec, how = CHN.match_paper(P('c', 'Notes on the Difference Engine and its Tabulation of Polynomials'), idx)
    assert how == 'title' and rec['oai_id'].endswith(':3')
    # a different author set, a year more than 2 apart, a short title, a deleted record, a relation DOI: no match
    assert CHN.match_paper(P('d', 'Notes on the Difference Engine and its Tabulation of Polynomials', byline=('X Y', 'Z W'), pis=('X Y',)), idx)[0] is None
    assert CHN.match_paper(P('e', 'Notes on the Difference Engine and its Tabulation of Polynomials', year=2010), idx)[0] is None
    assert CHN.match_paper(P('f', 'Short'), idx)[0] is None
    assert CHN.match_paper(P('g', 'x', doi='10.1234/del'), idx)[0] is None
    assert CHN.match_paper(P('h', 'x', doi='10.5555/rel'), idx)[0] is None
    # the paper's PI must be among the record's creators even when the byline overlaps
    assert CHN.match_paper(P('i', 'Notes on the Difference Engine and its Tabulation of Polynomials', pis=('Grace Hopper',)), idx)[0] is None


def test_open_files_skip_restricted_and_non_pdf():
    rec = dict(files=[dict(url='https://r/1.pdf', mime='application/pdf', kind='fulltext', access='http://purl.org/coar/access_right/c_abf2'),
                      dict(url='https://r/2.pdf', mime='application/pdf', kind='fulltext', access='http://purl.org/coar/access_right/c_14cb'),
                      dict(url='https://r/3.zip', mime='application/zip', kind='fulltext', access=None)])
    assert CHN.open_files(rec) == ['https://r/1.pdf']
    closed = dict(rec, rights=['restricted access'], links=['https://hdl.handle.net/1/2'])
    assert CHN.open_files(closed) == [] and CHN.candidate_rows('s', 'w', dict(closed, oai_id='x', title='t'), 'doi', {}) == []


def test_channel_interface_and_discover(store, monkeypatch):
    mod = CH.load('oai_repo')
    assert mod.NAME == 'oai_repo' and 'oai_repo' in CH.NATIVE
    seeded(store, [dc_record(1, LONG, ['Lovelace, Ada', 'Babbage, Charles'], ['https://doi.org/10.1145/abc', 'https://hdl.handle.net/1721.1/42'])])
    monkeypatch.setattr(CHN, '_cfg', lambda school: dict(CONF))
    ps = [P('a', LONG, doi='10.1145/abc'), P('b', 'No Such Paper In The Harvested Repository At All')]
    assert mod.APPLIES('s', ps[0]) is True
    known = defaultdict(set)
    ctx = types.SimpleNamespace(n=Counter(), known=known, dry=True, result=lambda p, st, urls=(), query=None, detail=None: CH.Result(p.key, p.work_id, st, urls, query, detail))
    res = {r.work_id: r for r in mod.discover('s', ps, ctx)}
    assert res['a'].status == 'found' and res['b'].status == 'none'
    assert res['a'].urls[0]['url'] == 'https://hdl.handle.net/1721.1/42' and res['a'].urls[0]['source'] == 'oai_repo_s'
    assert json.loads(res['a'].urls[0]['detail'])['match'] == 'doi' and ctx.n['oai_matched_doi'] == 1
    # a URL the work already holds is not a new row
    known['a'].add('https://hdl.handle.net/1721.1/42')
    ctx.n.clear()
    list(mod.discover('s', ps, ctx))
    assert ctx.n['oai_new_candidate_rows'] == 0


def test_figshare_oai_record_and_file_enrichment(store, monkeypatch):
    xml = (f'<OAI-PMH {NS}><ListRecords><record><header><identifier>oai:figshare.com:article/777</identifier><datestamp>2026-11-03T00:00:00Z</datestamp>'
           '<setSpec>portal_231</setSpec></header><metadata><oai_dc:dc><dc:title>' + LONG + '</dc:title><dc:creator>Ada Lovelace (13641862)</dc:creator>'
           '<dc:creator>Charles Babbage (4493710)</dc:creator><dc:identifier>10.1184/R1/777.v1</dc:identifier>'
           '<dc:relation>https://figshare.com/articles/journal_contribution/X/777</dc:relation><dc:relation>https://doi.org/10.9999/rel</dc:relation>'
           '<dc:date>2021-01-01T00:00:00Z</dc:date></oai_dc:dc></metadata></record></ListRecords></OAI-PMH>')
    recs, *_ = O.parse_page(xml)
    p = O.parse_record(recs[0], None, r'figshare\.com/articles/')
    assert p['creators'] == ['Ada Lovelace', 'Charles Babbage'] and p['links'] == ['https://figshare.com/articles/journal_contribution/X/777']
    c = O.connect('c')
    O.store_records(c, [p], 'portal_231')
    c.commit()
    conf = dict(CONF, enrich='figshare', enrich_base='https://api.figshare.com/v2')
    monkeypatch.setattr(CHN, '_cfg', lambda school: conf)
    api = json.dumps(dict(is_embargoed=False, is_confidential=False, license=dict(name='CC BY 4.0'),
                          files=[dict(name='paper.pdf', download_url='https://ndownloader.figshare.com/files/1'),
                                 dict(name='data.zip', download_url='https://ndownloader.figshare.com/files/2')]))
    asked = []
    ctx = types.SimpleNamespace(n=Counter(), known=defaultdict(set), dry=True, polite_get=lambda u, d: asked.append(u) or api,
                                result=lambda pp, st, urls=(), query=None, detail=None: CH.Result(pp.key, pp.work_id, st, urls, query, detail))
    res = list(CH.load('oai_repo').discover('c', [P('a', LONG, doi='10.1184/R1/777.v1')], ctx))
    assert asked == ['https://api.figshare.com/v2/articles/777']
    assert [u['url'] for u in res[0].urls] == ['https://ndownloader.figshare.com/files/1'] and res[0].urls[0]['license'] == 'CC BY 4.0'


def test_charter_verdicts(monkeypatch):
    from pathlib import Path
    import school_config as SC
    monkeypatch.setattr(SC, 'DIR', Path(__file__).resolve().parents[1] / 'schools')
    monkeypatch.setattr(SC, '_cache', {})
    seen = {k: SC.field(SC.get(k), 'oai_repo.verdict') for k in ('princeton', 'cmu', 'berkeley', 'stanford', 'epfl', 'mit', 'uchicago', 'gatech', 'michigan')}
    assert seen == dict(princeton='skip', cmu='harvest', berkeley='skip', stanford='skip', epfl='harvest', mit='harvest',
                    uchicago='harvest', gatech='skip', michigan=None)
    assert 'michigan' not in [k for k, v in seen.items() if v == 'harvest']   # owner rule: Deep Blue disallows AI agents by name
    assert not any('kilthub.cmu.edu' in SC.field(SC.get(k), 'oai_repo.base', '') for k in seen)
    for k in ('princeton', 'berkeley', 'stanford', 'gatech'):
        assert SC.field(SC.get(k), 'oai_repo.reason')


def rest_obj(i, title, doi=None, authors=('Lovelace, Ada',), issued='2020-05-01', rights='info:eu-repo/semantics/openAccess'):
    v = lambda *xs: [dict(value=x) for x in xs]  # noqa: E731
    md = {'dc.title': v(title), 'dc.contributor.author': v(*authors), 'dc.date.issued': v(issued), 'datacite.rights': v(rights),
          'dc.type': v('text::journal article')}
    if doi:
        md['dc.identifier.doi'] = v(doi)
    return dict(uuid=f'uuid-{i}', handle=f'20.500.14299/{i}', metadata=md)


def rest_page(objs, page, total):
    return json.dumps(dict(_embedded=dict(searchResult=dict(page=dict(number=page, totalPages=total),
                                                            _embedded=dict(objects=[dict(_embedded=dict(indexableObject=o)) for o in objs]))))).encode()


def test_rest_enumeration_pages_resumes_and_stores_records(store):
    conf = dict(rest_base='https://repo.example.edu/server/api', scopes=['20.500.14299/7'])
    r0 = Resp(json.dumps(dict(uuid='col-uuid')).encode())
    cl, _ = client([r0, Resp(rest_page([rest_obj(1, 'Paper One', '10.1234/one')], 0, 2)), Resp(b'', 403)])
    with pytest.raises(O.Blocked):
        O.harvest_rest('r', conf, cl, out=lambda *_: None)
    assert O.stats('r')['records'] == 1 and cl.s.calls[1]['scope'] == 'col-uuid' and cl.s.calls[1]['page'] == 0
    cl2, _ = client([Resp(rest_page([rest_obj(2, 'Paper Two')], 1, 2))])
    st = O.harvest_rest('r', conf, cl2, out=lambda *_: None)
    assert cl2.s.calls[0]['page'] == 1 and st['records'] == 2 and st['complete_sets'] == 1
    row = O.connect('r').execute("SELECT oai_id, dois, links, year, rights FROM records WHERE oai_id='rest:uuid-1'").fetchone()
    assert row[0] == 'rest:uuid-1' and json.loads(row[1]) == ['10.1234/one'] and json.loads(row[2]) == ['https://hdl.handle.net/20.500.14299/1'] and row[3] == 2020


def test_rest_record_bundle_files_become_candidates(store, monkeypatch):
    seeded_rest = O.connect('r')
    O.store_records(seeded_rest, [O.rest_record(rest_obj(7, LONG, '10.1234/seven'), 'rest:x')], 'rest:x')
    O.store_records(seeded_rest, [O.rest_record(rest_obj(8, 'A Closed Access Record Of Some Considerable Length', '10.1234/eight',
                                                        rights='info:eu-repo/semantics/restrictedAccess'), 'rest:x')], 'rest:x')
    seeded_rest.commit()
    conf = dict(CONF, enrich='dspace_bundles', enrich_base='https://repo.example.edu/server/api')
    monkeypatch.setattr(CHN, '_cfg', lambda school: conf)
    bundles = json.dumps(dict(_embedded=dict(bundles=[
        dict(name='ORIGINAL', _embedded=dict(bitstreams=dict(_embedded=dict(bitstreams=[
            dict(uuid='b1', name='paper.pdf', sizeBytes=10), dict(uuid='b2', name='data.zip', sizeBytes=10)])))),
        dict(name='THUMBNAIL', _embedded=dict(bitstreams=dict(_embedded=dict(bitstreams=[dict(uuid='b3', name='x.pdf', sizeBytes=1)]))))])))
    asked = []
    ctx = types.SimpleNamespace(n=Counter(), known=defaultdict(set), dry=True, polite_get=lambda u, d: asked.append(u) or bundles,
                                result=lambda p, st, urls=(), query=None, detail=None: CH.Result(p.key, p.work_id, st, urls, query, detail))
    res = {r.work_id: r for r in CH.load('oai_repo').discover('r', [P('a', LONG, doi='10.1234/seven'),
                                                                    P('b', 'x', doi='10.1234/eight')], ctx)}
    assert asked == ['https://repo.example.edu/server/api/core/items/uuid-7/bundles?embed=bitstreams']
    assert [u['url'] for u in res['a'].urls] == ['https://repo.example.edu/server/api/core/bitstreams/b1/content'] and res['b'].status == 'none'
