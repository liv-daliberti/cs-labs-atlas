"""R-PAP-31 (2026-11-05, the Georgia Tech stage-9 sample): a reply to a discussion or a quoted comment is a commentary, and a
special-issue preface is an editorial; each on the real items that failed, and the real papers around them stay."""
import pytest

from pihier import papers


def row(title, typ='article', venue='V', byline=('A B',), doi='10.1/x'):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=list(byline), authorship=dict(position='first'))


@pytest.mark.parametrize('title', [
    'Closure to “Macroelement and Macropatch Approaches to Structural Topology Optimization Using the Ground Structure Method”',
    'Discussion of “Data Fission: Splitting a Single Data Point” by Leiner et al.',
    "Authors' reply to the Discussion of ‘Estimating means of bounded random variables by betting’",
    'Comment on “SAT requires exhaustive search”',
    'Reply to ‘Human–AI complementarity needs augmentation, not emulation’'])
def test_R_PAP_31_replies_are_commentary(title):
    assert papers.not_a_paper(row(title)) == 'commentary'


@pytest.mark.parametrize('title', [
    'Special Topic on Monolithic 3-D Integration for Energy-Efficient Computing',
    'Special Issue on Top Picks From the 2025 Computer Architecture Conferences',
    'Special Section on Secure Computer Architectures',
    'Top Picks from the 2024 Computer Architecture Conferences'])
def test_R_PAP_31_special_issue_prefaces_are_editorials(title):
    assert papers.not_a_paper(row(title)) == 'editorial'


@pytest.mark.parametrize('title', [
    'Response to Intervention in Reading: A Randomized Trial',
    'Discussion Threads in Online Courses: A Study',
    'Comments on Code Review at Scale',
    'A Special Case of the Closure Problem',
    'Reply Prediction for Email Threads'])
def test_R_PAP_31_real_papers_stay(title):
    assert papers.not_a_paper(row(title)) is None
