"""Actual publication format, source genre and venue evidence must precede recovered edition/byline admission."""
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

FIXTURE = Path(__file__).parent / 'fixtures/recovered-source-quality.json'


def cases():
    out = json.loads(FIXTURE.read_text())['cases']
    for case in out:
        projection = {k: v for k, v in case.items() if k != 'projection_sha256'}
        assert hashlib.sha256(json.dumps(projection, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == case['projection_sha256']
    return out


def context(case):
    pid = case['pid']
    p = dict(pi=case['pi'], dblp=[pid])
    ctx = SimpleNamespace(n=Counter(), dblp_page_ranges={case['publication']['key']: case['pages']}, dblp_persons=dict(persons={pid: dict(pubs=[copy.deepcopy(case['publication'])])}), hits=[])
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
    row.update(oa=x['evidence'].get('oa') or 'https://dblp.org/rec/' + case['publication']['key'], work='fixture-work',
               byline_school=[], type=classified['type'], _source_quality_views=classified['quality_views'],
               _source_author_count=classified['author_count'], _source_page_evidence=classified['page_evidence'])
    pages = dict(doi=defaultdict(dict), title=defaultdict(dict))
    literal = case['pages']; count = page_count(literal); bare = bool(literal and '-' not in literal and '–' not in literal)
    pages['doi'][p['pi']][ndoi(row['doi'])] = (count, bare)
    pages['title'][p['pi']][norm_title(row['title'])] = (count, bare)
    authors = {p['pi']: {norm_title(row['title']): len(case['publication'].get('authors') or [])}}
    kept, _ = papers.drop_not_papers([row], authors, ctx.n, pages)
    kept, _ = papers.eligible_untranslated_sources(kept, 'cmu')
    return kept, ctx


@pytest.mark.parametrize('index', range(10))
def test_actual_source_bound_recoveries_use_format_genre_pages_and_canonical_venue(index):
    case = cases()[index]; before = copy.deepcopy(case)
    kept, ctx = evaluate(case)
    assert case == before
    assert bool(kept) == (case['expected'] == 'keep')
    assert ctx.recovered_source_quality[0]['owned_publications'][0]['record'] == case['publication']
    if kept:
        assert kept[0]['type'] in ['conference-paper', 'book-chapter']
        assert kept[0]['venue'] == case['recovery'].get('venue')
        assert '_source_quality_views' not in kept[0] and '_source_author_count' not in kept[0]
    else:
        assert ctx.n['not_paper_dropped'] == 1


@pytest.mark.parametrize('label', ['award_abstract', 'three_page_abstract', 'roman_page_keynote'])
def test_inproceedings_format_does_not_erase_actual_abstract_genre(label):
    case = next(c for c in cases() if c['label'] == label)
    assert case['publication']['type'] == 'inproceedings' and case['raw']['type'] == 'conference-abstract'
    kept, ctx = evaluate(case)
    assert not kept and ctx.n['not_paper:meeting_abstract:single_author'] == 1


@pytest.mark.parametrize('fault', ['pid', 'key', 'title', 'doi', 'kind', 'authors'])
def test_new_alternate_requires_exact_owned_publication_metadata(fault):
    case = next(c for c in cases() if c['label'] == 'english_chapter')
    ctx, p = context(case)
    if fault == 'pid':
        p['dblp'] = ['https://dblp.org/pid/different-owned-person']
    else:
        pub = ctx.dblp_persons['persons'][case['pid']]['pubs'][0]
        pub[dict(key='key', title='title', doi='dois', year='year', kind='type', authors='authors')[fault]] = dict(
            key='conf/other/Unrelated', title='A Different Source Paper', doi=['10.1/wrong'], year=2019, kind='www', authors=[['Another Person', None]])[fault]
    kept, ctx = evaluate(case, ctx, p)
    assert not kept and ctx.recovered_source_quality[0]['hold_reason']


@pytest.mark.parametrize('raw_state', ['absent', 'missing_doi'])
def test_missing_publication_doi_needs_an_exact_complete_raw_bridge_for_new_alternate(raw_state):
    case = copy.deepcopy(next(c for c in cases() if c['label'] == 'english_chapter'))
    ctx, p = context(case)
    if raw_state == 'absent':
        ctx.hits = []
    else:
        ctx.hits[0][1]['doi'] = None
    ctx.dblp_persons['persons'][case['pid']]['pubs'][0]['dois'] = []
    kept, ctx = evaluate(case, ctx, p)
    assert not kept and ctx.n['recovered_source_quality:new_alternate_doi_unproven'] == 1


def test_unknown_alternate_never_becomes_article_from_a_default():
    case = cases()[0]; ctx, p = context(case); ctx.dblp_persons = None
    x = copy.deepcopy(case['recovery'])
    assert papers.recovered_source_metadata(ctx, p, x, x['evidence'], 'dblp', strict=True) is None
    assert 'type' not in x


@pytest.mark.parametrize('key,expected', [('journals/corr/abs-2602-00669', 'preprint'),
                                         ('journals/neco/KramerC24', 'article')])
def test_exact_owned_corr_article_is_a_preprint_without_retyping_journal_articles(key, expected):
    # Regression: the reviewed Iglesias manuscript is a CoRR e-print even
    # though its native DBLP publication uses the same XML element as a journal.
    title = 'Improving Neuropathological Reconstruction Fidelity via AI Slice Imputation.'
    pid = 'https://dblp.org/pid/06/5946'
    record = dict(key=key, type='article', title=title, year=2026,
                  dois=['10.48550/arXiv.2602.00669'], authors=[['Juan Eugenio Iglesias', None]])
    ctx = SimpleNamespace(n=Counter(), dblp_persons=dict(persons={pid: dict(pubs=[record])}), hits=[])
    pi = dict(pi='Juan Eugenio Iglesias', dblp=[pid])
    recovery = dict(dblp_key=key, title=title, year=2026, doi=record['dois'][0], venue='CoRR')
    result = papers.recovered_source_metadata(ctx, pi, recovery, {}, 'dblp', strict=True)
    assert result['type'] == expected
    assert result['quality_views'] == [dict(type=expected, venue='CoRR')]
    # A repository key cannot authorize an unrelated publication projection.
    recovery['title'] = 'An unrelated paper'
    assert papers.recovered_source_metadata(ctx, pi, recovery, {}, 'dblp', strict=True) is None


def test_generic_journal_abbreviations_apply_only_to_quality_not_source_metadata():
    for short, canonical in [('Commun. ACM', 'Communications of the ACM'), ('IEEE Softw.', 'IEEE Software'),
                              ('IEEE Pervasive Comput.', 'IEEE Pervasive Computing')]:
        row = dict(venue=short, type='article', byline=['Ada Lovelace'])
        assert papers.quality_venue(short) == canonical and papers.short_piece(row, 3) == 'column'
        assert row['venue'] == short
    assert papers.short_piece(dict(venue='IEEE Software Engineering', type='article', byline=['Ada Lovelace']), 3) is None


def write_owned_publication(root, recovered, monkeypatch, pubtype='inproceedings', pages='1-12'):
    """A controlled complete owned-publication source for native tests; no publisher-kind fallback."""
    import gzip
    import test_build_rules as T
    from pihier import identity
    key = recovered['dblp_key'].removeprefix('https://dblp.org/rec/')
    pid = 'https://dblp.org/pid/fixture/Ada'
    publication = dict(key=key, type=pubtype, title=recovered['title'] + '.', year=recovered['year'],
                       dois=[recovered['doi']] if recovered.get('doi') else [],
                       authors=[[name, None] for name in recovered['byline']])
    packet = dict(persons={pid: dict(names=['Ada Lovelace'], affiliations=['Princeton University, NJ, USA'], pubs=[publication], orcid=[])},
                  by_name={'ada lovelace': [pid]})
    T.put(root, 'dblp-dump-persons.json.gz', None).write_bytes(gzip.compress(json.dumps(packet).encode()))
    T.put(root, 'dblp-dump-pages.json.gz', None).write_bytes(gzip.compress(json.dumps(dict(pages={key: pages})).encode()))
    monkeypatch.setattr(identity, 'DUMP_PERSONS', None)


@pytest.mark.usefixtures('layout')
def test_native_unknown_alternate_keeps_genuine_paper_but_cannot_lend_student_byline(tmp_path):
    import gzip
    import test_build_rules as T
    from pihier import links
    title = 'A Controlled Genuine Research Paper'
    raw = T.work('W601', title, 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1/w1')
    T.write_school(tmp_path, sweep=[raw])
    recovered = dict(pi='Ada Lovelace', dblp_key='conf/example/Unknown20', title=title, year=2020, doi='10.1/w1',
                     byline=['Ada Lovelace', 'Alan Turing'], venue='Proceedings', evidence=dict(
                         oa='https://dblp.org/rec/conf/example/Unknown20', basis='page1_publisher', how='publisher PDF',
                         url='https://example.edu/paper.pdf', pdf_sha256='a'*64, quotes=['Ada Lovelace, Princeton University']))
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    ctx = T.run_stages(tmp_path, upto='papers'); links.link_students(ctx)
    row = next(r for r in ctx.rows if r['pi'] == 'Ada Lovelace')
    assert row['oa'] == raw['id'] and not row['editions']
    assert ctx.n['recovered_source_quality:new_alternate_type_unproven'] == 1
    assert not any(s['student'] == 'p_alan' for s in ctx.sp)


@pytest.mark.usefixtures('layout')
def test_native_source_column_never_activates_an_inherited_verified_link(tmp_path, monkeypatch):
    import gzip
    import test_build_rules as T
    from pihier import links
    title = 'A Controlled Privacy Column'
    raw = T.work('W602', title, 2020, [T.au('Ada Lovelace', 'A1'), T.au('Linus Linked', 'A8')], doi='10.1/w1')
    raw['primary_location']['source']['display_name'] = 'Communications of the ACM'
    T.write_school(tmp_path, sweep=[raw])
    recovered = dict(pi='Ada Lovelace', dblp_key='journals/cacm/Fixture20', title=title, year=2020, doi='10.1/w1',
                     byline=['Ada Lovelace', 'Linus Linked'], venue='Commun. ACM', evidence=dict(
                         oa=raw['id'], basis='openalex_authorship', school_via=['Princeton University'], openalex_work=raw))
    write_owned_publication(tmp_path, recovered, monkeypatch, pubtype='article', pages='29-31')
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    before = T.run_stages(tmp_path, upto='students'); members = copy.deepcopy(before.stu)
    ctx = T.run_stages(tmp_path, upto='papers'); links.link_students(ctx)
    assert not any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
    assert not any(s['pi'] == 'Ada Lovelace' for s in ctx.sp)
    assert ctx.stu == members
    assert ctx.n['not_paper:column'] == 2  # raw source and recovery each pass the same rule


@pytest.mark.usefixtures('layout')
def test_native_inproceedings_does_not_erase_three_page_abstract_genre(tmp_path, monkeypatch):
    import gzip
    import test_build_rules as T
    title = 'A Controlled Invited Overview'
    raw = T.work('W603', title, 2020, [T.au('Ada Lovelace', 'A1')], doi='10.1/w1', typ='conference-abstract')
    T.write_school(tmp_path, sweep=[raw])
    recovered = dict(pi='Ada Lovelace', dblp_key='conf/example/Overview20', title=title, year=2020, doi='10.1/w1',
                     byline=['Ada Lovelace'], venue='Proceedings', evidence=dict(
                         oa=raw['id'], basis='openalex_authorship', school_via=['Princeton University'], openalex_work=raw))
    write_owned_publication(tmp_path, recovered, monkeypatch, pages='1-3')
    T.put(tmp_path, 'dblp-recovered.jsonl.gz').write_bytes(gzip.compress((json.dumps(recovered)+'\n').encode()))
    ctx = T.run_stages(tmp_path, upto='papers')
    assert not any(r['pi'] == 'Ada Lovelace' for r in ctx.rows)
    assert ctx.n['not_paper:meeting_abstract:single_author'] == 2


def test_exact_publication_author_count_cannot_borrow_a_same_title_copaper():
    case = next(c for c in cases() if c['label'] == 'one_page_invited')
    ctx, p = context(case); x = case['recovery']
    classified = papers.recovered_source_metadata(ctx, p, x, x['evidence'], 'dblp', strict=True)
    assert classified['author_count'] == 1
    row = dict(pi=p['pi'], oa='source-oa', doi=None, title=x['title'], year=x['year'], venue=x['venue'],
               byline=x['byline'], byline_school=[], type=classified['type'], _source_author_count=1)
    pages = dict(doi=defaultdict(dict), title=defaultdict(dict))
    pages['title'][p['pi']][norm_title(x['title'])] = (1, True)
    # An unrelated publication sharing the title cannot turn this exact single-author abstract into a paper.
    kept, _ = papers.drop_not_papers([row], {p['pi']: {norm_title(x['title']): 6}}, Counter(), pages)
    assert not kept



def test_explicit_nonpaper_source_type_is_not_erased_by_publication_format():
    case = copy.deepcopy(next(c for c in cases() if c['label'] == 'english_chapter'))
    case['recovery']['type'] = 'dataset'
    before = copy.deepcopy(case['recovery'])
    kept, ctx = evaluate(case)
    assert not kept and ctx.n['not_paper:source_type:dataset'] == 1
    assert case['recovery'] == before



def test_exact_publication_pages_cannot_borrow_a_longer_same_title_record():
    case = next(c for c in cases() if c['label'] == 'one_page_invited')
    ctx, p = context(case); x = case['recovery']
    classified = papers.recovered_source_metadata(ctx, p, x, x['evidence'], 'dblp', strict=True)
    assert classified['page_evidence'] == dict(key=case['publication']['key'], literal='1')
    row = dict(pi=p['pi'], oa='source-oa', doi=None, title=x['title'], year=x['year'], venue=x['venue'],
               byline=x['byline'], byline_school=[], type=classified['type'], _source_author_count=1,
               _source_page_evidence=classified['page_evidence'])
    pages = dict(doi=defaultdict(dict), title=defaultdict(dict))
    pages['title'][p['pi']][norm_title(x['title'])] = (12, False)
    kept, _ = papers.drop_not_papers([row], {p['pi']: {norm_title(x['title']): 1}}, Counter(), pages)
    assert not kept
