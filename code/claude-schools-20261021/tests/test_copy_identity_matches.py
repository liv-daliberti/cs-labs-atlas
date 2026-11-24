"""Coverage must bind stored bytes to an accepted work/edition, never merely a shared title."""
import pytest

import lab_paper_copies as C


TARGET = dict(work=None, oa='https://openalex.org/W2753377075', doi='10.14778/3137765.3137791',
              title='Mind the gap', year=2017,
              byline=['Christopher R. Aberger', 'Andrew Lamb', 'Kunle Olukotun', 'Christopher Ré'])
TARGET_ID = 'stanford_oa_W2753377075'
OTHER_ID = 'stanford_oa_W2984274416'


def test_mind_the_gap_other_paper_never_fills_the_exact_queued_work():
    """Actual audit: 2017 VLDB paper versus the 2019 HotNets PDF with different authors/DOI."""
    statuses = {TARGET_ID: 'queued', OTHER_ID: 'downloaded'}
    out, counts = C.resolve('stanford', [TARGET], statuses, {'10.1145/3365609.3365856': OTHER_ID}, {'mindthegap'})
    assert out[TARGET['oa']]['status'] == 'queued'
    assert out[TARGET['oa']]['catalog'] == TARGET_ID
    assert counts['local'] == 0


@pytest.mark.parametrize('year,byline', [(2017, TARGET['byline']), (2019, ['Jack Tigar Humphries', 'Kostis Kaffes']),
                                        (2017, ['Different Author']), (2026, TARGET['byline'])])
def test_title_only_never_proves_identity_even_without_a_known_conflict(year, byline):
    # Year/name agreement is not independently reviewed edition evidence either.
    paper = dict(TARGET, year=year, byline=byline)
    out, counts = C.resolve('stanford', [paper], {OTHER_ID: 'downloaded'}, {}, {'mindthegap'})
    assert out[paper['oa']]['status'] == 'not_in_catalog'
    assert out[paper['oa']]['catalog'] is None
    assert counts['local'] == 0


def test_exact_accepted_key_takes_priority_over_other_records_with_the_same_title():
    matches = {}
    out, counts = C.resolve('stanford', [dict(TARGET, work='accepted-work')],
                            {'accepted-work': 'downloaded', TARGET_ID: 'queued', OTHER_ID: 'downloaded'},
                            {TARGET['doi']: OTHER_ID}, {'mindthegap'}, matches=matches)
    assert out['accepted-work']['catalog'] == 'accepted-work'
    assert counts['local'] == 1
    assert matches['accepted-work'] == ('accepted-work', 'downloaded')


def test_exact_doi_copy_is_not_hidden_by_a_queued_accepted_key():
    out, counts = C.resolve('stanford', [TARGET], {TARGET_ID: 'queued', 'same-doi': 'downloaded'},
                            {TARGET['doi']: 'same-doi'}, {'mindthegap'})
    assert out[TARGET['oa']]['catalog'] == 'same-doi'
    assert out[TARGET['oa']]['status'] == 'downloaded'
    assert counts['local'] == 1


def test_exact_doi_normalization_preserves_a_real_copy_without_title_matching():
    out, counts = C.resolve('stanford', [dict(TARGET, doi='https://doi.org/10.14778/3137765.3137791')],
                            {'same-doi': 'downloaded'}, {TARGET['doi']: 'same-doi'}, set())
    assert out[TARGET['oa']]['catalog'] == 'same-doi'
    assert counts['local'] == 1


def test_explicit_accepted_edition_and_doi_alias_preserve_the_copy():
    paper = dict(TARGET, editions=[dict(work='reviewed-edition', oa=None, doi='10.1/accepted-edition', year=2019)])
    out, counts = C.resolve('stanford', [paper], {TARGET_ID: 'queued', 'canonical-edition': 'fulltext_xml'},
                            {}, set(), alias={'reviewed-edition': 'canonical-edition'})
    assert out[TARGET['oa']]['catalog'] == 'canonical-edition'
    assert counts['local'] == 1


def test_pending_or_quarantined_exact_matches_still_do_not_count():
    for status in ['identity_unconfirmed', 'quarantined_robots_ai']:
        out, counts = C.resolve('stanford', [TARGET], {TARGET_ID: status, OTHER_ID: 'downloaded'}, {}, {'mindthegap'})
        assert out[TARGET['oa']]['status'] == status
        assert counts['local'] == 0
