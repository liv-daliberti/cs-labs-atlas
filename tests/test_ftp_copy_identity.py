"""Collector seed suppression uses the same exact identities as copy coverage."""
from collections import defaultdict

import pytest

import ftp_common as F
import lab_paper_copies as C


TARGET = dict(work=None, oa='https://openalex.org/W2753377075', doi='10.14778/3137765.3137791',
              title='Mind the gap', year=2017)
TARGET_ID = 'stanford_oa_W2753377075'
OTHER_ID = 'stanford_oa_W2984274416'


def state(status, doi=None, title=None, local=None, alias=None):
    return dict(status=status, doi=doi or {}, title=title or {}, local=local or set(),
                alias=alias or {}, urls=defaultdict(set))


def check(paper, catalog, expected):
    assert F.match_work('stanford', paper, catalog) == expected
    out, counts = C.resolve('stanford', [paper], catalog['status'], catalog['doi'],
                            set(catalog['title']), alias=catalog['alias'])
    key = paper['work'] or paper['oa']
    assert out[key]['catalog'] == expected
    assert F.is_local('stanford', paper, catalog) == bool(counts['local'])


def test_actual_mind_the_gap_different_doi_stays_missing():
    """2017 VLDB target versus physically checked 2019 HotNets work from the audit."""
    catalog = state({TARGET_ID: 'queued', OTHER_ID: 'downloaded'},
                    {'10.1145/3365609.3365856': OTHER_ID}, {'mindthegap': OTHER_ID},
                    {'t:mindthegap', 'doi:10.1145/3365609.3365856', OTHER_ID})
    check(TARGET, catalog, TARGET_ID)
    assert not F.is_local('stanford', TARGET, catalog)


def test_long_title_without_identifiers_never_selects_other_work():
    paper = dict(TARGET, title='A sufficiently long shared paper title')
    title = F.nt(paper['title'])
    catalog = state({OTHER_ID: 'downloaded'}, title={title: OTHER_ID}, local={'t:' + title})
    check(paper, catalog, None)


@pytest.mark.parametrize('identity', ['accepted_work', 'oa', 'doi', 'arxiv', 'edition_work', 'edition_oa', 'edition_doi', 'edition_alias'])
def test_all_exact_identities_can_find_a_local_copy_after_queued_target(identity):
    paper = dict(TARGET)
    status = {TARGET_ID: 'queued', 'copy': 'downloaded'}
    doi, alias = {}, {}
    if identity == 'accepted_work':
        paper['work'] = 'copy'
    elif identity == 'oa':
        status[TARGET_ID] = 'downloaded'
    elif identity == 'doi':
        paper['doi'] = 'HTTPS://DOI.ORG/' + TARGET['doi']
        doi[TARGET['doi']] = 'copy'
    elif identity == 'arxiv':
        paper['arxiv'] = '1701.01234'
        doi['10.48550/arxiv.1701.01234'] = 'copy'
    else:
        edition = dict(work=None, oa=None, doi=None)
        paper['editions'] = [edition]
        if identity == 'edition_work':
            edition['work'] = 'copy'
        elif identity == 'edition_oa':
            edition['oa'] = 'https://openalex.org/W123'
            status['stanford_oa_W123'] = status.pop('copy')
        elif identity == 'edition_doi':
            edition['doi'] = 'https://doi.org/10.1/reviewed-edition'
            doi['10.1/reviewed-edition'] = 'copy'
        else:
            edition['work'] = 'reviewed-edition'
            alias['reviewed-edition'] = 'copy'
    expected = TARGET_ID if identity == 'oa' else 'stanford_oa_W123' if identity == 'edition_oa' else 'copy'
    check(paper, state(status, doi=doi, alias=alias), expected)
    assert F.is_local('stanford', paper, state(status, doi=doi, alias=alias))


@pytest.mark.parametrize('status', ['queued', 'identity_unconfirmed', 'quarantined_robots_ai', 'copy_quality_unconfirmed'])
def test_stale_local_title_or_doi_sets_never_override_ineligible_exact_status(status):
    catalog = state({TARGET_ID: status}, {TARGET['doi']: TARGET_ID}, {'mindthegap': TARGET_ID},
                    {'t:mindthegap', 'doi:' + TARGET['doi'], TARGET_ID})
    check(TARGET, catalog, TARGET_ID)
    assert not F.is_local('stanford', TARGET, catalog)


def test_first_eligible_exact_copy_keeps_counter_priority_and_xml_counts():
    paper = dict(TARGET, work='accepted', editions=[dict(work='edition', oa=None)])
    check(paper, state({'accepted': 'fulltext_xml', TARGET_ID: 'downloaded', 'edition': 'downloaded'}), 'accepted')
