"""Explicit source genre labels are paratext; research mentioning them stays."""
import pytest

from pihier.papers import not_a_paper


@pytest.mark.parametrize('title', [
    "Accessibility [Guest editor's introduction]",
    "Accessible systems [Guest editors’ introduction]",
    "Computing for everyone (Guest editors' preface)",
    "Systems [guest-editor note].",
])
def test_explicit_final_guest_editor_label_is_editorial(title):
    assert not_a_paper(dict(title=title, type='article', venue='Research Journal', byline=['A', 'B'])) == 'editorial'


@pytest.mark.parametrize('title', [
    "Accessibility: An introduction to assistive technology",
    "Understanding guest editors' introduction practices",
    "A study of [Guest editor's introduction] labels in scientific publishing",
    "Accessibility [Guest editor's introduction)",
    "Accessibility (Guest editor's introduction]",
    "Accessibility [An introduction]",
])
def test_ordinary_research_and_nonlabels_remain(title):
    assert not_a_paper(dict(title=title, type='article', venue='Research Journal', byline=['A', 'B'])) is None
