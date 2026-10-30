"""Discovery channel plugins (fulltext-push/channels/, channel_runner.py; docs/CHANNELS.md; 2026-10-30): the interface of
every plugin on fixture papers, the legacy adapter's Results, and the runner's known-URL filtering and dry run."""
import sys
import types
from collections import defaultdict
from pathlib import Path

import pytest

FTP = Path(__file__).resolve().parents[1] / 'fulltext-push'
if str(FTP) not in sys.path:
    sys.path.append(str(FTP))
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
    recs = [('2101.00001', 'Learning Fixture Representations for Channel Plugins', ('lovelace', 'babbage'), 2020),
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
    r = dict(title='Learning Fixture Representation for Channel Plugins', year=2021, byline=['Ada Lovelace', 'Charles Babbage'], pis=['Ada Lovelace'])
    best, d = A.match(r)
    assert best[0] == '2101.00001' and d['similarity'] >= A.MIN_SIM
    assert A.match(dict(r, byline=['Grace Hopper', 'Ada Lovelace']))[0] is None       # another author set
    assert A.match(dict(r, year=2025))[0] is None                                       # outside the year window
    assert A.same_authors(['Lovelace, Ada', 'Babbage, Charles'], [], ('lovelace', 'babbage', 'x'))


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
