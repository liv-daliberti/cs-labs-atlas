"""A trailing front-matter label is not a research title mentioning prefaces."""
import pytest

from pihier.papers import not_a_paper


@pytest.mark.parametrize('title', [
    'Data through the Computational Lens, Preface for ICCS 2016',
    'Parallel Computing: Preface to the special issue',
    'Machine Learning — Preface',
])
def test_explicit_trailing_preface_is_editorial(title):
    row = dict(title=title, type='conference-paper', venue='Procedia Computer Science',
               byline=['Michael L. Norman', 'Other Editor'])
    assert not_a_paper(row) == 'editorial'


@pytest.mark.parametrize('title', [
    'Automatic Detection of Prefaces in Scientific Books',
    'Classifying Front Matter: Prefaces and Introductions',
    'Predicting Editorial Decisions with Machine Learning',
    'A Framework for ICCS 2016 Data Analysis',
])
def test_research_about_prefaces_and_editorial_work_remains_eligible(title):
    row = dict(title=title, type='conference-paper', venue='Research Conference',
               byline=['Ada Researcher', 'Another Researcher'])
    assert not_a_paper(row) is None
