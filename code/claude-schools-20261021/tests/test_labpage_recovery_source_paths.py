"""Primary-source recovery keeps literal names and publisher-owned PDF routes."""
import re

import pytest

import labpage_recover as R


@pytest.mark.parametrize(('author', 'pi_institution', 'other_institution', 'accepted'), [
    ('Jon Donnelly', 'Johns Hopkins University', 'Duke University', True),
    ('Jonathan Donnelly', 'Johns Hopkins University', 'Duke University', True),
    ('Jon Donnelly', 'Duke University', 'Johns Hopkins University', False),
    ('Jane Donnelly', 'Johns Hopkins University', 'Duke University', False),
])
def test_literal_pi_spelling_keeps_own_affiliation_required(author, pi_institution, other_institution, accepted):
    title = 'Local understanding of covariate importance with conditional density estimation'
    page = f'{title} {author}1 Alice Smith2 1 {pi_institution} 2 {other_institution} Abstract Results'
    how, _, _ = R.page1_tie(page, R.name_forms(['Jon Donnelly']),
                          re.compile(R.AFF['jhu'], re.I), [R.norm_title(title)])
    assert bool(how and how != 'title_not_on_page1') == accepted


def test_pmlr_publisher_mirrors_are_derived_from_the_same_volume_and_paper():
    assert R.proceedings_links({'links': ['https://proceedings.mlr.press/v300/gao26a.html']}) == [
        'https://proceedings.mlr.press/v300/gao26a/gao26a.pdf',
        'https://proceedings.mlr.press/v300/gao26a.pdf',
        'https://raw.githubusercontent.com/mlresearch/v300/main/assets/gao26a/gao26a.pdf',
    ]


@pytest.mark.parametrize('url', [
    'https://raw.githubusercontent.com/someone/other/main/paper.pdf',
    'https://example.org/paper.pdf',
    'https://dl.acm.org/doi/pdf/10.1145/123',
])
def test_publisher_mirrors_do_not_enable_arbitrary_pdf_hosts(url):
    assert R.proceedings_links({'links': [url]}) == []
