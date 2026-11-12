"""R-PAP-40 (2026-11-12, stage-9 genre rules for the legacy schools: CMU, Berkeley, Stanford, MIT lab-paper samples); each on the real failing row."""
import pytest

from pihier import papers


def row(title, typ='article', venue='V', byline=('A B',), doi='10.1/x'):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=list(byline), authorship=dict(position='first'))


def test_book_review_type_is_not_a_paper():
    r = row('Robots, telework, and the jobs of the future The Globotics Upheaval: Globalization, Robotics, and the Future of Work Richard Baldwin Oxford University Press, 2019. 300 pp.',
            typ='book-review', venue='Science', byline=('Jon Peha',), doi='10.1126/science.aav6273')
    assert papers.not_a_paper(r) == 'book_review'
    assert papers.not_a_paper(dict(r, type='article', title='Robots and the future of work')) is None
