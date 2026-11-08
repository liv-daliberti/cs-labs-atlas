"""Independent audit regressions: issue editorials are paratext; published editions lead deposits."""
import collections

import pytest

from pihier import papers


@pytest.mark.parametrize('title', [
    'PACMHCI V10, N2 CSCW April 2026 Editorial CSCW001',
    'PACMHCI V10, N6, October 2026 Editorial',
    'PACMMOD, V4, N2 (PODS), May 2026 Editorial',
    'Inaugural Editorial from the New Editor-in-Chief',
    'JOURNAL V12, N4, March 2027 Editorial J004',
])
def test_issue_and_inaugural_editorials_are_not_research_articles(title):
    assert papers.not_a_paper(dict(title=title, type='article', venue='Research journal',
                                   doi='10.1/article', byline=['Alice Author', 'Bob Author'])) == 'editorial'


@pytest.mark.parametrize('title', [
    'Predicting Editorial Decisions with Neural Language Models',
    'Measuring Editorial Bias in Scientific Peer Review',
    'Analyzing PACMHCI V10, N2 CSCW April 2026 Editorial Decisions',
])
def test_research_about_editorial_decisions_stays(title):
    assert papers.not_a_paper(dict(title=title, type='article', venue='Research journal',
                                   doi='10.1/research', byline=['Alice Author', 'Bob Author'])) is None


def row(oa, doi, venue, **extra):
    return dict(pi='Example PI', work=None, oa=oa, doi=doi, venue=venue, year=2023,
                title='Practically Adopting Human Activity Recognition', type='conference-paper',
                byline=['Huatao Xu', 'Pengfei Zhou', 'Rui Tan', 'Mo Li'], byline_school=['Mo Li'], **extra)


@pytest.mark.parametrize('reverse', [False, True])
def test_published_proceedings_leads_same_title_zenodo_deposit(reverse):
    deposit = row('zenodo', '10.5281/zenodo.8260607', 'Zenodo')
    published = row('acm', '10.1145/3570361.3613299', 'MobiCom proceedings')
    records = [deposit, published] if not reverse else [published, deposit]
    n = collections.Counter()
    result = papers.merge_editions(records, n)
    assert len(result) == 1 and result[0]['oa'] == 'acm'
    assert result[0]['editions'][0]['oa'] == 'zenodo'
    assert len(result[0]['_bylines']) == 2 and n['edition_records_merged'] == 1


def test_explicit_source_metadata_outweighs_a_deposit_doi_and_collection_id():
    deposit = row('repository', '10.9000/deposit', 'Unfamiliar repository')
    deposit.update(work='collection-deposit', year=2026,
                   _edition_source=dict(source_type='repository', version='submittedVersion', is_published=False))
    published = row('published', None, 'Unfamiliar publisher')
    published['_edition_source'] = dict(source_type='conference', version='publishedVersion', is_published=True)
    result = papers.merge_editions([deposit, published], collections.Counter())[0]
    assert result['oa'] == 'published'
    assert result['editions'][0]['oa'] == 'repository'
    assert '_edition_source' not in result   # internal source evidence is not a package schema change


def test_a_repository_only_paper_is_retained():
    deposit = row('repository', '10.5281/zenodo.8260607', 'Zenodo')
    result = papers.merge_editions([deposit], collections.Counter())
    assert len(result) == 1 and result[0]['oa'] == 'repository'


def test_edition_source_keeps_native_publication_metadata_only():
    evidence = papers.edition_source(dict(primary_location=dict(
        source=dict(type='conference', display_name='Proceedings'),
        version='publishedVersion', is_published=True, landing_page_url='https://example.test/paper')))
    assert evidence == dict(source_type='conference', version='publishedVersion', is_published=True)


def test_a_published_venue_location_outweighs_a_broad_preprint_type():
    deposit = row('deposit', '10.9000/deposit', 'Repository',
                  _edition_source=dict(source_type='repository', version='submittedVersion', is_published=False))
    published = row('published', '10.9000/published', 'Conference',
                    _edition_source=dict(source_type='conference', version='publishedVersion', is_published=True))
    published['type'] = 'preprint'
    assert papers.merge_editions([deposit, published], collections.Counter())[0]['oa'] == 'published'
