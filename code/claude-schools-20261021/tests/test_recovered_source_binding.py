"""Owned literal aliases and publication format never rewrite dates or lend another author's school."""
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from dblp_dump_pages import page_count
from pihier import papers
from pihier.common import ndoi, norm_title
from pihier.names import Name, byline_name

FIXTURE = Path(__file__).parent / 'fixtures/recovered-source-binding.json'


def cases():
    rows = json.loads(FIXTURE.read_text())['cases']
    for row in rows:
        projection = {k: v for k, v in row.items() if k != 'projection_sha256'}
        assert hashlib.sha256(json.dumps(projection, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == row['projection_sha256']
    return rows


def source_case(key):
    return next(c for c in cases() if c['role'] == 'source_binding' and c['publication']['key'] == key)


def context(case):
    p = dict(pi=case['pi'], names=case['names'], dblp=[case['pid']])
    person = dict(names=case['pid_selfnames'], pubs=[copy.deepcopy(case['publication'])])
    ctx = SimpleNamespace(n=Counter(), dblp_page_ranges={case['publication']['key']: case['pages']},
                          dblp_persons=dict(persons={case['pid']: person}), hits=[])
    if case['raw']:
        ctx.hits.append((p['pi'], copy.deepcopy(case['raw']), None, None, None, None))
    return ctx, p


def evaluate(case, ctx=None, p=None):
    if ctx is None:
        ctx, p = context(case)
    x = copy.deepcopy(case['recovery'])
    classified = papers.recovered_source_metadata(ctx, p, x, x['evidence'], 'dblp', strict=True)
    if classified is None:
        return [], ctx
    row = {k: x.get(k) for k in ['pi', 'doi', 'title', 'year', 'venue', 'byline']}
    row.update(oa=x['evidence'].get('oa') or 'https://dblp.org/rec/'+case['publication']['key'], work='fixture-work',
               byline_school=[], type=classified['type'], _source_quality_views=classified['quality_views'],
               _source_author_count=classified['author_count'], _source_page_evidence=classified['page_evidence'])
    pages = dict(doi=defaultdict(dict), title=defaultdict(dict))
    literal = case['pages']; count = page_count(literal); bare = bool(literal and '-' not in literal and '–' not in literal)
    pages['doi'][p['pi']][ndoi(row.get('doi'))] = (count, bare)
    pages['title'][p['pi']][norm_title(row['title'])] = (count, bare)
    kept, _ = papers.drop_not_papers([row], {}, ctx.n, pages)
    kept, _ = papers.eligible_untranslated_sources(kept, 'cmu')
    return kept, ctx


@pytest.mark.parametrize('index', range(109))
def test_actual_owned_sources_and_all_95_nonpaper_controls(index):
    case = cases()[index]; before = copy.deepcopy(case)
    kept, ctx = evaluate(case)
    assert case == before
    assert bool(kept) == (case['expected'] != 'drop')
    proof = ctx.recovered_source_quality[-1]
    assert proof['owned_publications'][0]['record'] == case['publication']
    assert proof['year'] == case['recovery']['year']
    if kept:
        assert kept[0]['year'] == case['recovery']['year']
    # A format-positive case is explicitly NOT a full scientific admission/genre/date certificate.


@pytest.mark.parametrize('key', ['conf/nips/SwamyCBW22', 'conf/aistats/DickLPWBS17', 'conf/nips/KohFS23', 'conf/nips/EysenbachUSL22'])
def test_actual_alias_families_are_attested_only_on_the_exact_owned_publication(key):
    case = source_case(key); ctx, p = context(case); before = copy.deepcopy((ctx.dblp_persons, p, case['recovery']))
    authors = [a[0] for a in case['publication']['authors']]
    assert not any(Name(p['names']).match(byline_name(a)) for a in authors)
    kept, ctx = evaluate(case, ctx, p)
    assert kept
    assert (ctx.dblp_persons, p, case['recovery']) == before
    binding = papers.recovered_publication_binding(ctx, p, case['recovery'], case['recovery']['evidence'], 'dblp')
    assert any(Name(binding['names']).match(byline_name(a)) for a in authors)


@pytest.mark.parametrize('fault', ['pid', 'key', 'title', 'doi', 'authors', 'other_pid_alias', 'other_publication_alias'])
def test_alias_authority_cannot_escape_the_exact_owned_publication(fault):
    case = source_case('conf/nips/SwamyCBW22'); ctx, p = context(case)
    person = ctx.dblp_persons['persons'][case['pid']]; pub = person['pubs'][0]
    if fault == 'pid':
        p['dblp'] = ['https://dblp.org/pid/another-person']
    elif fault == 'key':
        pub['key'] = 'conf/other/Unrelated'
    elif fault == 'title':
        pub['title'] = 'A Different Publication'
    elif fault == 'doi':
        pub['dois'] = ['10.1/another-work']
    elif fault == 'authors':
        pub['authors'] = [['A Different Author', None]]
    elif fault == 'other_pid_alias':
        ctx.dblp_persons['persons']['https://dblp.org/pid/not-owned'] = copy.deepcopy(person)
        person['names'] = ['Steven Wu']
    else:
        unrelated = copy.deepcopy(pub); unrelated['key'] = 'conf/other/Unrelated'
        person['pubs'].append(unrelated)
        person['names'] = ['Steven Wu']
    kept, _ = evaluate(case, ctx, p)
    assert not kept
    binding = papers.recovered_publication_binding(ctx, p, case['recovery'], case['recovery']['evidence'], 'dblp')
    assert binding['names'] == p['names']


@pytest.mark.parametrize('key', ['conf/corl/FitzgeraldKCWSK22', 'conf/amf/LiuFNP14', 'conf/atal/KaurNS14',
                               'conf/mkm/BentkampA21', 'conf/istar/BreauxGYALP24', 'conf/innovations/FilmusOW19'])
def test_format_pages_authority_preserves_both_years_without_changing_recovery_date(key):
    case = source_case(key); before = copy.deepcopy(case)
    kept, ctx = evaluate(case)
    assert kept and case == before
    proof = ctx.recovered_source_quality[-1]
    assert proof['year_disagreements'] == [dict(pid=case['pid'], key=key, publication_year=case['publication']['year'], recovery_year=case['recovery']['year'])]
    assert 'publication_year_disagreement' in proof['review_reasons']
    assert kept[0]['year'] == case['recovery']['year'] != case['publication']['year']
    assert ctx.n['recovered_source_review:publication_year_disagreement'] == 1
    if key == 'conf/mkm/BentkampA21':
        assert 'work_in_progress_genre_review' in proof['review_reasons']
    if key == 'conf/istar/BreauxGYALP24':
        assert 'panel_report_genre_review' in proof['review_reasons']


@pytest.mark.usefixtures('layout')
@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('fault', [None, 'own_school', 'raw_title', 'raw_doi', 'period', 'window', 'pubkey', 'arxiv_date'])
def test_native_exact_alias_recovery_replays_own_school_and_ordinary_date_guards(tmp_path, monkeypatch, fault, existing):
    import test_build_rules as T
    raw = T.work('WBIND', 'Learning to Compute', 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1/w1')
    T.write_school(tmp_path, sweep=[raw] if existing else []); ctx = T.run_stages(tmp_path, upto='hits')
    p = ctx.pid0['Ada Lovelace']; p['dblp'] = ['https://dblp.org/pid/owned']
    key = 'conf/example/Owned19'
    pub = dict(key=key, title='Learning to Compute.', year=2019, type='inproceedings', dois=['10.1/w1'], authors=[['Ada Byron', None], ['Alan Turing', None]])
    ctx.dblp_persons = dict(persons={p['dblp'][0]: dict(names=['Ada Lovelace', 'Ada Byron'], pubs=[pub])})
    own = T.au('Ada Byron', 'A1', school=fault != 'own_school', raw=['Elsewhere University'] if fault == 'own_school' else None)
    source = T.work('WBIND', raw['title'], 2020, [own, T.au('Alan Turing', 'A9')], doi=raw['doi'])
    recovery = dict(pi=p['pi'], dblp_key=key, title=raw['title'], year=2020, doi=raw['doi'], venue='Proceedings',
                    byline=['Ada Byron', 'Alan Turing'], evidence=dict(oa=raw['id'], basis='openalex_authorship', school_via=['Princeton University'], openalex_work=source))
    if fault == 'period':
        p['periods'] = [dict(id='future', start='2021', end=None, asof=None)]; p['listings'] = []
    elif fault == 'window':
        recovery['year'] = 2015
    elif fault == 'pubkey':
        recovery['dblp_key'] = 'conf/other/Unrelated'
    elif fault == 'raw_title':
        source['title'] = 'An Unrelated Work With A Different Affiliation'
    elif fault == 'raw_doi':
        source['doi'] = '10.1/another-work'
    elif fault == 'arxiv_date':
        recovery['evidence'].update(basis='page1_arxiv', url='https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/1501/1501.00001v1.pdf', how='marker')
    original = copy.deepcopy((p, recovery, source, pub))
    monkeypatch.setattr(papers, 'recovered_source', lambda c, kind: [recovery] if kind == 'dblp' else [])
    papers.lab_papers(ctx)
    assert bool(ctx.n['dblp_recovered_lab_papers']) is (fault is None)
    assert (p, recovery, source, pub) == original
    if fault is None:
        row = next(r for r in ctx.rows if r['pi'] == p['pi'])
        assert row['year'] == 2020 and row['appointment']['periodId'] == 'reviewed:ada-lovelace:1'
        assert any('Ada Byron' in byline for byline, _ in row['_bylines'])
    if fault in ['raw_title', 'raw_doi']:
        assert ctx.n['recovered_school_scope_alias_source_conflict'] == 1


def test_actual_ryan_conference_remains_distinct_from_same_oa_journal():
    case = source_case('conf/innovations/FilmusOW19'); ctx, p = context(case)
    kept, ctx = evaluate(case, ctx, p); conf = kept[0]
    conf.update(work='conference-work', date=str(conf['year']), landing='publisher-source', authorship={}, identity='dblp_person_page', appointment={'periodId': 'reviewed'})
    journal = dict(conf, work='journal-work', doi='10.1214/22-ejp749', year=2022, date='2022-01-01', type='article',
                   title='Log-Sobolev inequality for the multislice, with applications', byline=['Yuval Filmus', 'Ryan O’Donnell', 'Xinyu Wu'])
    before = copy.deepcopy([journal, conf]); n = Counter(); diagnostics = []
    unique = papers.collapse_eligible_sources([journal, conf], n, diagnostics=diagnostics)
    rows = papers.merge_editions(unique, n, diagnostics=diagnostics)
    assert [journal, conf] == before and len(rows) == 2
    assert {r['doi'] for r in rows} == {'10.1214/22-ejp749', '10.4230/lipics.itcs.2019.34'}
    assert {r['work'] for r in rows} == {'journal-work', 'conference-work'}
    assert all(not r['editions'] for r in rows)
    assert any(d.get('reason') == 'distinct_populated_doi_components' for d in diagnostics)
