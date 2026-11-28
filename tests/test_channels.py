"""Discovery channel plugins (fulltext-push/channels/, channel_runner.py; docs/CHANNELS.md; 2026-10-30): the interface of
every plugin on fixture papers, the legacy adapter's Results, and the runner's known-URL filtering and dry run."""
import types
from collections import defaultdict
from pathlib import Path

import pytest

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
import channels as CH  # noqa: E402
import channel_runner as R  # noqa: E402
import lab_channels as L  # noqa: E402

ROWS = [  # fixture lab papers: (row, catalog work id)
    (dict(work='w1', oa='https://openalex.org/W1', doi='10.1145/3000001', title='A Study of Fixture Papers for Channel Plugins', year=2021,
          byline=['Ada Lovelace'], pis=['Ada Lovelace'], editions=[]), 'w1'),
    (dict(work='w2', oa='https://openalex.org/W2', doi=None, title='Another Fixture Paper Without Any Identifier', year=2019,
          byline=['Alan Turing'], pis=['Alan Turing'], editions=[]), 'w2'),
    (dict(work=None, oa='https://openalex.org/W3', doi='10.48550/arxiv.2101.00001', title='Short', year=2020, byline=[], pis=['Grace Hopper'],
          editions=[]), 'w3'),
]


def papers(known=None):
    known = known or defaultdict(set)
    return [CH.Paper(r['work'] or r['oa'], w, r, set(known[w])) for r, w in ROWS], known


LEGACY = [n for n in CH.NAMES if n not in CH.NATIVE]


def test_every_step_is_a_plugin():
    assert set(LEGACY) == set(L.STEPS)
    assert sorted(p.stem for p in (FTP / 'channels').glob('*.py') if not p.stem.startswith('_')) == sorted(CH.NAMES)


@pytest.mark.parametrize('change', [dict(), dict(title='A Study of Fixture Papers for Channel Plugins Part II'),
                                  dict(authors=[dict(name='Grace Hopper')]), dict(yearPublished=2016),
                                  dict(yearPublished=None), dict(doi='10.1145/9999999')])
def test_core_title_requires_complete_matching_metadata(change, monkeypatch):
    from channels import core_title as C
    import core_search
    monkeypatch.setattr(core_search, 'usable', lambda u: u.startswith('https://repo.example.edu/'))
    record = dict(title=ROWS[0][0]['title'], authors=[dict(name='Ada Lovelace')], yearPublished=2021,
                  doi=None, sourceFulltextUrls=['https://repo.example.edu/paper.pdf', 'https://core.ac.uk/reader/1'])
    record.update(change)
    assert C.matching_links(record, ROWS[0][0]) == ([] if change else ['https://repo.example.edu/paper.pdf'])


def test_core_title_dry_run_uses_cache_without_request_or_write(tmp_path, monkeypatch):
    import json
    import bulk_oa
    import core_search
    from channels import core_title as C
    monkeypatch.setattr(bulk_oa, 'DIR', tmp_path)
    doi_cache = tmp_path / 'doi-cache.jsonl'
    doi_cache.write_text(json.dumps(dict(doi=ROWS[0][0]['doi'], links=[])) + '\n')
    monkeypatch.setattr(core_search, 'CACHE', doi_cache)
    monkeypatch.setattr(C, 'search', lambda *a: pytest.fail('dry run queried CORE'))
    ps, known = papers()
    ctx = R.Ctx('uestc', ps, known, dry=True)
    chosen = [p for p in ps if C.APPLIES('uestc', p)]
    out = list(C.discover('uestc', chosen, ctx))
    assert len(out) == 1 and out[0].status == 'none'
    assert ctx.n['core_title_to_ask'] == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ['doi-cache.jsonl']


@pytest.mark.parametrize('status', [400, 401, 403, 429, 503])
def test_core_title_stops_after_one_api_error(status, monkeypatch):
    from channels import core_title as C
    monkeypatch.setattr(C.time, 'sleep', lambda _: None)
    calls = []
    session = types.SimpleNamespace(get=lambda *a, **k: calls.append(k) or types.SimpleNamespace(status_code=status))
    ps, known = papers()
    ctx = R.Ctx('uestc', ps, known, dry=False)
    assert C.search(session, 'title:"fixture"', ctx) is None
    assert len(calls) == 1 and ctx.n[f'core_title_http_{status}'] == 1
    assert ctx.n['stopped']


def test_core_title_queries_individual_titles(tmp_path, monkeypatch):
    import json
    import bulk_oa
    import core_search
    from channels import core_title as C
    monkeypatch.setattr(C.time, 'sleep', lambda _: None)
    monkeypatch.setattr(bulk_oa, 'DIR', tmp_path)
    monkeypatch.setattr(L.F.P, 'FT_LOGS', tmp_path)
    second = dict(ROWS[0][0], doi='10.1234/fixture2', title='A Different Complete Fixture Title for CORE Discovery')
    rows = [ROWS[0][0], second]
    cache = tmp_path / 'doi-cache.jsonl'
    cache.write_text(''.join(json.dumps(dict(doi=r['doi'], links=[])) + '\n' for r in rows))
    monkeypatch.setattr(core_search, 'CACHE', cache)
    ps = [CH.Paper(f'w{i}', f'w{i}', r, set()) for i, r in enumerate(rows)]
    ctx = R.Ctx('uestc', ps, defaultdict(set), dry=False)
    calls = []
    def get(*args, **kwargs):
        calls.append(kwargs['params']['q'])
        return types.SimpleNamespace(status_code=200, headers={}, json=lambda: dict(results=[]))
    monkeypatch.setattr(ctx, 'session', lambda: types.SimpleNamespace(headers={}, get=get))
    monkeypatch.setattr(ctx, 'env', lambda _: 'fixture-key')
    result = list(C.discover('uestc', ps, ctx))
    assert len(calls) == 2 and all(' OR ' not in q for q in calls)
    assert all(r.status == 'none' for r in result)


@pytest.mark.parametrize('name', LEGACY)
def test_plugin_interface_on_fixtures(name, monkeypatch):
    mod = CH.load(name)
    assert mod.NAME == name
    ps, known = papers()
    for school in ('princeton', 'berkeley', 'mit', 'epfl'):
        for p in ps:
            assert isinstance(mod.APPLIES(school, p), bool)
    # the step's body replaced by a fixture: it finds one PDF for w1 and writes one URL for w2 itself
    def fake(school, miss, known_, n):
        known_['w2'].add('https://repo.example.edu/w2.pdf')
        return [dict(work_id='w1', url='https://lab.example.edu/w1.pdf', landing_url=None, version=None, source=name, detail=None)]
    monkeypatch.setitem(L.STEPS, name, fake)
    ctx = R.Ctx('mit', ps, known, dry=True)
    chosen = [p for p in ps if mod.APPLIES('mit', p)]
    res = {r.work_id: r for r in mod.discover('mit', chosen, ctx)}
    assert res['w1'].status == 'found' and res['w1'].urls[0]['url'] == 'https://lab.example.edu/w1.pdf'
    assert res['w2'].status == 'found' and res['w2'].urls[0].get('written_by_step')
    for p in ps:
        if p.work_id not in ('w1', 'w2') and mod.APPLIES('mit', p):
            assert res[p.work_id].status == 'none'
        if p.work_id not in res:
            assert not mod.APPLIES('mit', p)


def test_stopped_step_reports_error(monkeypatch):
    def fake(school, miss, known_, n):
        n['openalex_budget_stop'] = 1
        return []
    monkeypatch.setitem(L.STEPS, 'oa_editions', fake)
    ps, known = papers()
    ctx = R.Ctx('mit', ps, known, dry=True)
    mod = CH.load('oa_editions')
    out = list(mod.discover('mit', [p for p in ps if mod.APPLIES('mit', p)], ctx))
    assert out and all(r.status == 'error' for r in out)


def test_runner_filters_known_urls_and_writes_nothing_dry(monkeypatch):
    fake = types.SimpleNamespace(NAME='fake', APPLIES=lambda s, p: True,
                                 discover=lambda s, ps, ctx: [ctx.result(p, 'found', ['https://x.example.edu/a.pdf', 'https://x.example.edu/b.pdf'])
                                                              if p.work_id == 'w1' else ctx.result(p, 'none') for p in ps])
    monkeypatch.setattr(CH, 'load', lambda name: fake)
    monkeypatch.setattr(L, 'write', lambda school, rows, step, ev_dir=None, dry=False: 0 if dry else pytest.fail('dry run wrote'))
    known = defaultdict(set, {'w1': {'https://x.example.edu/a.pdf'}})
    rows, n = R.run_channel('mit', 'fake', [(r, w) for r, w in ROWS], known, dry=True, log=False)
    assert [r['url'] for r in rows] == ['https://x.example.edu/b.pdf']
    assert rows[0]['source'] == 'fake' and 'https://x.example.edu/b.pdf' in known['w1']


def test_result_status_is_closed():
    with pytest.raises(AssertionError):
        CH.Result('k', 'w', 'maybe')


def test_arxiv_loose_matches_only_the_same_author_set(monkeypatch):
    from channels import arxiv_loose as A
    import arxiv_oai as ao
    recs = [('2101.00001', 'FixRep: Learning Fixture Representations for Channel Plugins', ('lovelace', 'babbage'), 2020),
            ('2101.00002', 'Learning Fixture Representations for Channel Plugin Systems', ('hopper',), 2020),
            ('2101.00003', 'Learning Fixture Representations for Channel Plugins', ('lovelace', 'babbage'), 2010)]
    post = defaultdict(list)
    built = []
    for i, (aid, t, fams, y) in enumerate(recs):
        ws = frozenset(ao.words(t))
        built.append((aid, t, fams, y, ws))
        for w in ws:
            post[w].append(i)
    monkeypatch.setattr(A, '_IDX', dict(recs=built, post=post, ao=ao))
    r = dict(title='Learning Fixture Representations for Channel Plugins', year=2021, byline=['Ada Lovelace', 'Charles Babbage'], pis=['Ada Lovelace'])
    best, d = A.match(r)
    assert best[0] == '2101.00001' and d['similarity'] >= A.MIN_SIM
    assert A.match(dict(r, byline=['Grace Hopper', 'Ada Lovelace']))[0] is None       # another author set
    assert A.match(dict(r, year=2025))[0] is None                                       # outside the year window
    assert A.same_authors(['Lovelace, Ada', 'Babbage, Charles'], [], ('lovelace', 'babbage', 'x'))
    assert not A.strict_ok('Two More Attacks on Proof-of-Stake', 'Two Attacks on Proof-of-Stake', 0.95, 0.86)       # a word of its own
    assert not A.strict_ok('On Satisfiable k-CSPs: II', 'On Satisfiable k-CSPs: VII', 0.99, 0.9)                   # another part
    assert not A.strict_ok('Rejoinder: Coauthorship Networks for Statisticians', 'Coauthorship Networks for Statisticians', 0.91, 0.8)


def test_ledger_found_turns_tokens_into_candidates(monkeypatch):
    from channels import ledger_found as LF
    import ftp_common as F
    import s2_key_lookup as s2k
    monkeypatch.setattr(LF, '_CACHE', {'mit': {'w1': dict(key='w1', new_open_urls=['arXiv:2101.00001', 'PMC123', 'https://repo.example.edu/a.pdf'],
                                                          checks=[dict(source='s2', result='found')], checked_at='2026-10-30')}})
    monkeypatch.setattr(s2k, 'pmc_files', lambda s, p, memo: [f'https://pmc-oa-opendata.s3.amazonaws.com/PMC{p}.1/PMC{p}.1.pdf'])
    monkeypatch.setattr(F, 'bulk_rows', lambda want, src: ([dict(work_id=w, url=f'https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{a}.pdf',
                                                                 landing_url=None, version=None, source=src, detail=a) for w, a in want.items()], 0))
    ps, known = papers()
    ctx = R.Ctx('mit', ps, known, dry=True)
    chosen = [p for p in ps if LF.APPLIES('mit', p)]
    assert [p.key for p in chosen] == ['w1']
    (res,) = list(LF.discover('mit', chosen, ctx))
    assert res.status == 'found' and len(res.urls) == 3


def test_oa_publisher_asks_the_publishers_open_location(monkeypatch):
    from channels import oa_publisher as OP
    oa = dict(source='openalex', result='none', detail=dict(locations=[
        dict(is_oa=True, type='journal', landing='http://www.example-journal.org/a/1', pdf=None),
        dict(is_oa=False, type='repository', landing='https://repo.example.edu/1', pdf='https://repo.example.edu/1.pdf')]))
    monkeypatch.setattr(OP, '_CACHE', {'mit': {
        'w1': dict(key='w1', doi='10.5555/abc', oa_status='gold', publisher='Example', checks=[oa]),
        'w2': dict(key='w2', doi='10.1109/xyz', oa_status='hybrid', publisher='IEEE', checks=[oa])}})
    ps, known = papers()
    assert [p.key for p in ps if OP.APPLIES('mit', p)] == ['w1']       # IEEE (a bot challenge) is left alone
    ctx = R.Ctx('mit', ps, known, dry=True)
    (res,) = list(OP.discover('mit', [ps[0]], ctx))
    assert res.urls[0]['url'] == 'https://www.example-journal.org/a/1' and res.urls[0]['landing_url'] == 'http://www.example-journal.org/a/1'


@pytest.fixture
def bulk_here(monkeypatch):
    """This checkout's bulk_oa: another test removes this directory from sys.path, after which a main checkout's older copy can answer the import."""
    import sys
    monkeypatch.syspath_prepend(str(FTP))
    monkeypatch.delitem(sys.modules, 'bulk_oa', raising=False)


def test_bulk_oa_matching_order_doi_then_arxiv_then_title_author(bulk_here):
    import bulk_oa as B
    rows = [dict(school='mit', key='k1', work_id='w1', doi='10.1/abc', arxiv=None, nt='learningfixturerepresentationsforchannelplugins', fam=['lovelace'], year=2021),
            dict(school='mit', key='k2', work_id='w2', doi=None, arxiv='2101.00002', nt='shorttitle', fam=['hopper'], year=2020)]
    ix = B.index(rows)
    assert B.match_record(ix, doi='https://doi.org/10.1/ABC')[0] == 'doi'
    assert B.match_record(ix, arxiv='2101.00002v3')[0] == 'arxiv'
    how, hit = B.match_record(ix, title='Learning Fixture Representations for Channel Plugins', first_family='lovelace', year=2020)
    assert how == 'title_author' and hit[0]['key'] == 'k1'
    assert B.match_record(ix, title='Learning Fixture Representations for Channel Plugins', first_family='babbage', year=2021)[0] is None  # another first author
    assert B.match_record(ix, title='Learning Fixture Representations for Channel Plugins', first_family='lovelace', year=2030)[0] is None  # year window


def test_s2_bulk_channel_reads_the_local_table(monkeypatch):
    from channels import s2_bulk as SB
    import ftp_common as F
    import s2_key_lookup as s2k
    rec = dict(corpusid=1, how='doi', doi='10.1145/3000001', arxiv='2101.00001', pmc=None, acl='2021.acl-long.1', targets=[['mit', 'w1', 'w1']],
               pdfurls=['https://lab.example.edu/w1.pdf', 'https://dl.acm.org/doi/pdf/10.1145/3000001'], oainfo=dict(openaccessurl='https://repo.example.edu/w1.pdf', license='cc-by'))
    monkeypatch.setattr(SB, '_T', dict(by={('mit', 'w1'): [rec]}, release='2026-10-27'))
    monkeypatch.setattr(F, 'bulk_rows', lambda want, src: ([dict(work_id=w, url=f'https://storage.googleapis.com/arxiv-dataset/{a}.pdf', source=src) for w, a in want.items()], 0))
    monkeypatch.setattr(s2k, 'pmc_files', lambda *a: [])
    ps, known = papers()
    ctx = R.Ctx('mit', ps, known, dry=True)
    chosen = [p for p in ps if SB.APPLIES('mit', p)]
    assert [p.key for p in chosen] == ['w1']
    (res,) = list(SB.discover('mit', chosen, ctx))
    urls = {u['url'] for u in res.urls}
    assert 'https://lab.example.edu/w1.pdf' in urls and 'https://repo.example.edu/w1.pdf' in urls and 'https://aclanthology.org/2021.acl-long.1.pdf' in urls
    assert not any('dl.acm.org' in u for u in urls) and any('arxiv-dataset' in u for u in urls)  # ACM refuses automated clients


def test_arxiv_bulk_matches_by_doi_then_exact_title_and_authors(monkeypatch, bulk_here):
    from channels import arxiv_bulk as AB
    import ftp_common as F
    t = 'Learning Fixture Representations for Channel Plugins'
    ix = dict(by_doi={'10.1145/3000001': ('2101.00001', 'A Study of Fixture Papers: the preprint', ('lovelace',), 2020)},
              by_t={F.nt(t): [('2101.00002', t, ('lovelace', 'babbage'), 2020)]}, n=2)
    ps, known = papers()
    assert AB.match(ps[0].r, ix)[0] == 'doi'
    r = dict(title=t, year=2021, byline=['Ada Lovelace', 'Charles Babbage'], pis=['Ada Lovelace'], doi=None)
    assert AB.match(r, ix) == ('title_author', ix['by_t'][F.nt(t)][0])
    assert AB.match(dict(r, byline=['Grace Hopper', 'Charles Babbage']), ix)[0] is None
    assert AB.match(dict(r, year=2028), ix)[0] == 'title_author'  # accepted eight-year publication lag
    assert AB.match(dict(r, year=2029), ix)[0] is None
    assert AB.match(dict(r, year=2018), ix)[0] is None  # preprint cannot follow the paper by two years


def test_oa_locations_reads_every_location_and_sibling_records(monkeypatch):
    from channels import oa_locations as OL
    import bulk_oa as B
    import ftp_common as F
    t = 'A Study of Fixture Papers for Channel Plugins'
    own = dict(id='https://openalex.org/W1', type='article', locations=[dict(pdf_url='https://repo.example.edu/own.pdf', landing_page_url=None, is_oa=True, source=dict(type='repository', display_name='R'), version='publishedVersion')])
    sib = dict(id='https://openalex.org/W9', type='article', publication_year=2020, authorships=[dict(author=dict(display_name='Ada Lovelace'))],
               locations=[dict(pdf_url='https://lab.example.edu/accepted.pdf', landing_page_url='https://lab.example.edu/p', is_oa=True, version='acceptedVersion', source=dict(type='repository', display_name='L'))],
               best_oa_location=dict(pdf_url='https://best.example.edu/b.pdf', landing_page_url=None, is_oa=True), open_access=dict(oa_url='https://oa.example.edu/x.pdf'))
    monkeypatch.setattr(B, 'oa_stores', lambda: [])
    monkeypatch.setattr(B, 'title_index', lambda: {F.nt(t): ['https://openalex.org/W9']})
    monkeypatch.setattr(B, 'oa_by_doi', lambda stores, doi: [])
    monkeypatch.setattr(B, 'oa_by_id', lambda stores, wid: sib)
    monkeypatch.setattr(F, 'oa_bodies', lambda school, ids: {i: own for i in ids})
    ps, known = papers()
    ctx = R.Ctx('mit', ps, known, dry=True)
    (res,) = [r for r in OL.discover('mit', [ps[0]], ctx)]
    urls = {u['url'] for u in res.urls}
    assert {'https://repo.example.edu/own.pdf', 'https://lab.example.edu/accepted.pdf', 'https://best.example.edu/b.pdf', 'https://oa.example.edu/x.pdf'} <= urls
    assert OL.siblings.__name__ == 'siblings'


def test_wayback_escholarship_applies_only_to_berkeley_papers_known_on_escholarship():
    from channels import wayback_escholarship as WE
    ps, known = papers(known=defaultdict(set, {'w1': {'https://escholarship.org/uc/item/1wt3d4vr', 'https://escholarship.org/content/qt1wt3d4vr/qt1wt3d4vr.pdf'}}))
    assert WE.item_ids(ps[0].known) == ['1wt3d4vr']
    assert WE.APPLIES('berkeley', ps[0]) and not WE.APPLIES('mit', ps[0]) and not WE.APPLIES('berkeley', ps[1])


def test_oa_locations_siblings_need_the_same_article_like_type(monkeypatch):
    from channels import oa_locations as OL
    import bulk_oa as B
    import ftp_common as F
    t = 'A Study of Fixture Papers for Channel Plugins'
    sib = dict(id='https://openalex.org/W9', type='book-chapter', publication_year=2020, authorships=[dict(author=dict(display_name='Ada Lovelace'))], locations=[])
    monkeypatch.setattr(B, 'title_index', lambda: {F.nt(t): ['https://openalex.org/W9']})
    monkeypatch.setattr(B, 'oa_by_doi', lambda stores, doi: [])
    monkeypatch.setattr(B, 'oa_by_id', lambda stores, wid: sib)
    ps, known = papers()
    assert OL.siblings(ps[0], [], B.title_index(), dict(id='https://openalex.org/W1', type='article')) == []      # a chapter is not the article
    assert OL.siblings(ps[0], [], B.title_index(), dict(id='https://openalex.org/W1', type='book')) == []         # a book has no siblings
    assert OL.siblings(ps[0], [], B.title_index(), dict(id='https://openalex.org/W1', type='book-chapter')) == []
    assert OL.siblings(ps[0], [], B.title_index(), None) == []


def test_title_compatible_rejects_another_part_and_keeps_a_retitled_preprint(bulk_here):
    import bulk_oa as B
    assert not B.title_compatible('Efficient Multiparty Interactive Coding - Part II: Non-Oblivious Noise', 'Efficient Multiparty Interactive Coding for Insertions, Deletions and Substitutions')
    assert not B.title_compatible('Language, Stapp, and the Mind/Body/World Problem', 'Towards a Science of Mind')
    assert B.title_compatible('On the complexity and verification of quantum random circuit sampling', 'Quantum Supremacy and the Complexity of Random Circuit Sampling')
    assert B.title_compatible('Interactive cryptographic proofs of quantumness using mid-circuit measurements', 'Interactive Proofs of Quantumness via Mid-Circuit Measurements')


def test_core_api_channels_are_enabled_for_every_school(monkeypatch):
    import ftp_common as F
    assert not F.CORE_PAUSED and not F.PAUSED_CHANNELS
    calls = []
    fake = types.SimpleNamespace(APPLIES=lambda school, paper: True,
                                 discover=lambda school, papers, ctx: calls.append((school, len(papers))) or [])
    monkeypatch.setattr(CH, 'load', lambda name: fake)
    monkeypatch.setattr(L, 'write', lambda school, rows, step, dry=False: 0)
    for school in ('mit', 'toronto'):
        _, known = papers()
        rows, _ = R.run_channel(school, 'core_bulk', [(r, w) for r, w in ROWS], known, dry=True, log=False)
        assert rows == []
    assert calls == [('mit', len(ROWS)), ('toronto', len(ROWS))]


def test_sonar_asks_only_ids_named_by_known_urls_and_takes_unrestricted_pdfs():
    from channels import sonar as SO
    ps, known = papers(known=defaultdict(set, {'w1': {'https://sonar.ch/global/documents/264649', 'https://folia.unifr.ch/global/documents/202705'}}))
    assert SO.doc_ids(ps[0].known) == ['202705', '264649']
    assert SO.APPLIES('epfl', ps[0]) and not SO.APPLIES('epfl', ps[1])
    rec = dict(metadata=dict(_files=[dict(key='fulltext.pdf', restriction=dict(restricted=False), permissions=dict(read=True)),
                                     dict(key='fulltext-pdf.jpg'), dict(key='embargoed.pdf', restriction=dict(restricted=True))]))
    assert SO.open_pdf_keys(rec) == ['fulltext.pdf']
    assert SO.open_pdf_keys(dict(metadata=dict(_files=[]))) == []
