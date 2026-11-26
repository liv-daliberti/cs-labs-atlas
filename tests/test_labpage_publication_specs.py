"""A reviewed publication card selector survives the school adapter and source changes reopen it."""
from types import SimpleNamespace

import pytest

import labpage_audit as L


URL = 'https://example.edu/group/publications/'
SHA = 'a' * 64
SPEC = dict(item='article.pub', title='p.ti', year='p.vn', venue='p.vn')


def plan(page, captured_sha=SHA):
    kit = SimpleNamespace(src_of=lambda u: u, stored=lambda u: (dict(sha256=captured_sha), {}) if captured_sha else (None, None))
    ctx = dict(school='jhu', cfg=dict(family='test'), manual={}, pubs_rows_pages={})
    return L.adapter_plan(kit, ctx, dict(pi='Example PI'), dict(pubs_pages=[page]))


def test_reviewed_title_and_entry_selectors_are_preserved():
    page = dict(url=URL, sha256=SHA, spec=SPEC.copy())
    result = plan(page)['pubs'][0]
    assert result['spec'] == SPEC
    assert result['pubs_page'] == URL
    result['spec']['title'] = '.different'
    assert page['spec']['title'] == 'p.ti'


@pytest.mark.parametrize('captured_sha', ['b' * 64, None])
def test_changed_or_missing_original_does_not_reuse_selectors(captured_sha):
    with pytest.raises(ValueError, match='do not match the retained original'):
        plan(dict(url=URL, sha256=SHA, spec=SPEC), captured_sha)


@pytest.mark.parametrize('page', [dict(url=URL, spec=SPEC), dict(url=URL, sha256='not-a-hash', spec=SPEC),
                                  dict(url=URL, sha256=SHA, spec='article.pub')])
def test_explicit_selectors_need_valid_source_binding(page):
    with pytest.raises(ValueError, match='require their original source hash'):
        plan(page)


def test_unconfigured_legacy_publication_page_keeps_default_extraction():
    assert plan(dict(url=URL), None)['pubs'][0]['spec'] == {}


def external_review(sha=SHA):
    return dict(publication_section_review=dict(url=URL, sha256=sha, reviewed_by='source reviewer',
                reviewed_on='2026-11-24', whole_source_read=True, disposition='external_index_only'))


def test_only_the_reviewed_external_index_document_is_excluded():
    kit = SimpleNamespace(stored=lambda src: (dict(sha256=SHA), {}))
    other = dict(pubs_page=URL + 'actual-papers')
    pages, reviewed = L.reviewed_external_index(kit, external_review(), [dict(pubs_page=URL), other])
    assert reviewed and pages == [other]


@pytest.mark.parametrize('captured_sha', ['b' * 64, None])
def test_changed_external_index_document_reopens_review(captured_sha):
    kit = SimpleNamespace(stored=lambda src: (dict(sha256=captured_sha), {}) if captured_sha else (None, None))
    with pytest.raises(ValueError, match='review must be reopened'):
        L.reviewed_external_index(kit, external_review(), [dict(pubs_page=URL)])


def test_partial_external_index_source_review_cannot_suppress_a_page():
    prior = external_review()
    prior['publication_section_review']['whole_source_read'] = False
    with pytest.raises(ValueError, match='complete original source binding'):
        L.reviewed_external_index(None, prior, [dict(pubs_page=URL)])


def manual_publication_plan(entry_changes=None, metadata_changes=None, returned_changes=None):
    entry = dict(title='An actual listed paper', year=2026, url=URL, sha256=SHA, quote='An actual listed paper')
    entry.update(entry_changes or {})
    page = dict(url=URL, sha256=SHA, reviewed_entries=[entry], whole_source_read=True,
                reviewed_by='Independent source reviewer', reviewed_on='2026-11-24')
    page.update(metadata_changes or {})
    def check(school, title, year, source, **kwargs):
        assert school == 'jhu' and source == SHA
        if kwargs['quote'] != 'An actual listed paper':
            raise ValueError('not a literal source quote')
        return dict(title=title, year=year, venue=kwargs.get('venue'), links=kwargs.get('links') or [],
                    url=URL, sha256=SHA, quote=kwargs['quote'], **(returned_changes or {}))
    kit = SimpleNamespace(src_of=lambda u: u, stored=lambda u: (dict(sha256=SHA), {}),
                          lpev=SimpleNamespace(P=check))
    ctx = dict(school='jhu', cfg=dict(family='test'), manual={}, pubs_rows_pages={})
    return L.adapter_plan(kit, ctx, dict(pi='Example PI'), dict(pubs_pages=[page]))


def test_explicit_reviewed_publications_use_checked_manual_plan_entries():
    result = manual_publication_plan()['pubs']
    assert len(result) == 1 and result[0]['title'] == 'An actual listed paper'
    assert 'pubs_page' not in result[0]  # The extractor must not replace a whole-source manual reading.


@pytest.mark.parametrize('metadata', [dict(whole_source_read=False), dict(reviewed_by=''),
                                      dict(reviewed_on=''), dict(reviewed_entries=[]), dict(spec=SPEC)])
def test_manual_publication_entries_need_complete_unambiguous_review(metadata):
    with pytest.raises(ValueError, match='whole-source review'):
        manual_publication_plan(metadata_changes=metadata)


@pytest.mark.parametrize('changes', [dict(pi='Different PI'), dict(sha256='b' * 64),
                                    dict(title=''), dict(quote=''), dict(year='2026'), dict(year=True)])
def test_manual_publication_entries_cannot_reassign_or_malformed_the_source(changes):
    with pytest.raises(ValueError, match='malformed source-bound'):
        manual_publication_plan(entry_changes=changes)


def test_manual_publication_quote_is_rechecked_on_the_retained_original():
    with pytest.raises(ValueError, match='not a literal source quote'):
        manual_publication_plan(entry_changes=dict(quote='Invented publication'))


@pytest.mark.parametrize('changes', [dict(url='https://different.example/papers'),
                                    dict(capture_url='https://archive.example/different')])
def test_manual_publication_quote_cannot_resolve_to_different_source(changes):
    with pytest.raises(ValueError, match='different retained source'):
        manual_publication_plan(entry_changes=changes)


def test_all_explicitly_reviewed_pages_are_read_beyond_legacy_four_page_limit():
    pages = [dict(url=f'{URL}{i}', sha256=SHA, spec=SPEC) for i in range(8)]
    kit = SimpleNamespace(src_of=lambda u: u, stored=lambda u: (dict(sha256=SHA), {}))
    ctx = dict(school='jhu', cfg=dict(family='test'), manual={}, pubs_rows_pages={})
    result = L.adapter_plan(kit, ctx, dict(pi='Example PI'), dict(pubs_pages=pages))
    assert len(result['pubs']) == 8
    ctx['pubs_rows_pages'] = {'Example PI': [f'{URL}{i}' for i in range(8)]}
    assert len(L.adapter_plan(kit, ctx, dict(pi='Example PI'), {})['pubs']) == 4


@pytest.mark.parametrize('configured', [dict(spec=SPEC), dict(reviewed_entries=[dict(title='First paper')])])
def test_duplicate_explicit_publication_sources_cannot_choose_last(configured):
    kit = SimpleNamespace(src_of=lambda u: u, stored=lambda u: (dict(sha256=SHA), {}))
    ctx = dict(school='jhu', cfg=dict(family='test'), manual={}, pubs_rows_pages={})
    first = dict(url=URL, sha256=SHA, **configured)
    second = dict(first, reviewed_entries=[dict(title='Different paper')])
    with pytest.raises(ValueError, match='duplicate explicitly reviewed'):
        L.adapter_plan(kit, ctx, dict(pi='Example PI'), dict(pubs_pages=[first, second]))


@pytest.mark.parametrize('kind', sorted(L.REVIEWED_NONPAPER_KINDS))
def test_source_reviewed_nonpaper_kind_is_carried_with_its_literal_proof(kind):
    fields = dict(excluded_kind=kind, exclusion_reason='Independent source review of this exact source entry',
                  exclusion_quote='An actual listed paper')
    result = manual_publication_plan(entry_changes=fields)['pubs'][0]
    assert all(result[key] == value for key, value in fields.items())


@pytest.mark.parametrize('fields', [dict(excluded_kind='extended_abstract', exclusion_reason='Bad blanket rule',
                                        exclusion_quote='An actual listed paper'),
                                    dict(excluded_kind='invited_talk'), dict(exclusion_reason='No type or proof'),
                                    dict(excluded_kind='thesis', exclusion_reason='', exclusion_quote='An actual listed paper')])
def test_partial_or_ineligible_nonpaper_decisions_fail_closed(fields):
    with pytest.raises(ValueError, match='incomplete reviewed publication-kind'):
        manual_publication_plan(entry_changes=fields)


def test_nonpaper_type_proof_must_be_literal_on_the_bound_original():
    with pytest.raises(ValueError, match='not a literal source quote'):
        manual_publication_plan(entry_changes=dict(excluded_kind='thesis', exclusion_reason='Source says thesis',
                                                   exclusion_quote='Invented thesis claim'))


def test_nonpaper_observation_does_not_suppress_same_title_research_paper(monkeypatch):
    research = dict(title='A scientific result', year=2018, quote='A scientific result', url=URL, sha256=SHA)
    talk = dict(research, year=2019, excluded_kind='invited_talk', exclusion_reason='Single-author invited lecture',
                exclusion_quote='A scientific result: invited lecture')
    other_version = dict(research, year=2020, venue='CS conference extended abstract')
    monkeypatch.setattr(L, 'paper_sources', lambda *args: ([], [talk, research, other_version]))
    ctx = dict(prior={}, lab_papers={'Example PI': [dict(title=research['title'], year=2018)]})
    p = dict(pi='Example PI')
    section, entries = L.collect_papers(None, ctx, p, dict(status='found'), {})
    assert len(entries) == 1 and entries[0]['year'] == 2018 and entries[0]['match'] == 'title'
    assert section['listed'] == 2 and section['matched_in_lab_papers'] == 1
    assert len(section['reviewed_nonpaper_observations']) == 1
    assert section['missing'][0]['reason_code'] == 'not_a_paper'
    assert section['duplicate_listing_observations'][0]['year'] == 2020
    monkeypatch.setattr(L, 'pi_start_year', lambda p: 2016)
    assert L.finish_papers(section, entries, p, {}) == []
    assert section['reason_code'] == 'all_missing_explained'


def test_remote_extractor_fields_cannot_exclude_a_paper(monkeypatch):
    remote = dict(title='A scientific result', year=2026, quote='A scientific result',
                  excluded_kind='thesis', exclusion_reason='Untrusted remote claim', exclusion_quote='anything')
    kit = SimpleNamespace(pubx=SimpleNamespace(extract=lambda *args: (dict(url=URL, sha256=SHA), [remote])))
    monkeypatch.setattr(L, 'paper_sources', lambda *args: ([dict(pubs_page=URL)], []))
    ctx = dict(school='jhu', prior={}, lab_papers={'Example PI': [dict(title=remote['title'], year=2026)]})
    section, entries = L.collect_papers(kit, ctx, dict(pi='Example PI'), dict(status='found'), {})
    assert len(entries) == 1 and entries[0]['match'] == 'title'
    assert 'reviewed_nonpaper_observations' not in section and section['missing'] == []
