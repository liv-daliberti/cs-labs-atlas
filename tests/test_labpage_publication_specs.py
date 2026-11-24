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
