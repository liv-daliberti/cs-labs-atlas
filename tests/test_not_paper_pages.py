"""R-PAP-27 (2026-11-02, the Michigan stage-9 sample): commentaries by title, magazine columns and keynote or invited abstracts
by page count (DBLP's `pages`, tools/dblp_dump_pages.py), each on the real item that failed; the page signal never fires
without a page count, and the real papers around it stay."""
import collections

import pytest

import dblp_dump_pages as D
import pi_hierarchy as h
from pihier import papers


def row(title, typ='article', venue='Communications of the ACM', byline=('A B',), doi='10.1145/1'):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=list(byline), authorship=dict(position='first'))


def test_R_PAP_27_page_count():
    assert [D.page_count(x) for x in ('502-503', '97', '28-30', '12:1-12:20', 'e123', '', None, '5-3')] == [2, 1, 3, 20, None, None, None, None]
    assert papers.page_count is D.page_count


@pytest.mark.parametrize('title', ['Technical perspective: How economic theories can help computers beat the heat',
                                   'Technical Perspective', 'Technical perspective: Is there a geek gene?'])
def test_R_PAP_27_commentary_title(title):                      # Wenisch and Guzdial, CACM 2019 (pages 97-97)
    assert h.not_a_paper(row(title)) == 'commentary'


def test_R_PAP_27_commentary_title_keeps_papers():
    assert h.not_a_paper(row('Technical debt in machine learning systems')) is None
    assert h.not_a_paper(row('A technical perspective on blockchain scalability')) is None  # not the column's opening


def test_R_PAP_27_column_by_pages():
    r = row('Computational thinking should just be good thinking', byline=list('abcd'))
    assert h.not_a_paper(r) is None                   # no page count: nothing to go on
    assert h.not_a_paper(r, 3) == 'column'            # CACM Viewpoint, pp. 28-30
    assert h.not_a_paper(r, 8) is None                # a research article
    assert h.not_a_paper(row('x', venue='IEEE Micro'), 2) == 'column'
    assert h.not_a_paper(row('x', venue='Computer'), 3) == 'column'
    for v in ('Computer Networks', 'Computer Speech & Language', 'Computer Communications', 'Computer Physics Communications'):
        assert h.not_a_paper(row('x', venue=v), 3) is None   # journals whose names start with 'Computer'


def test_R_PAP_27_bare_page_number():
    q = row('Troubling Trends in Machine Learning Scholarship', venue='Queue')    # DBLP '80' is ACM Queue's article number
    assert h.not_a_paper(q, 1, bare=True) is None and h.not_a_paper(q, 1) == 'column'
    assert h.not_a_paper(row('Technical thing', venue='Communications of the ACM'), 1, bare=True) == 'column'   # CACM '97' is page 97
    k = row('The role of cryo-CMOS in quantum computers', typ='conference-paper', venue='IWASI')
    assert h.not_a_paper(k, 1, bare=True) == 'invited_abstract'                   # IWASI 2019 keynote, DBLP '1'


def test_R_PAP_27_invited_abstract_by_pages():
    r = row('Computing Education as a Foundation for 21st Century Literacy', typ='conference-paper', venue='SIGCSE')
    assert h.not_a_paper(r, 2) == 'invited_abstract'  # SIGCSE 2019, pp. 502-503, a keynote abstract
    assert h.not_a_paper(r, 3) is None and h.not_a_paper(r) is None
    assert h.not_a_paper(dict(r, byline=['A B', 'C D']), 2) is None   # two authors: a short paper
    assert h.not_a_paper(dict(r, type='article'), 2) is None


def test_R_PAP_27_build_guard_dblp_coauthors():
    """OpenAlex cut the byline of a short conference paper: the PI's DBLP page lists it with co-authors, so it is kept."""
    n = collections.Counter()
    r = dict(row('Inter-triggering hybrid automata', typ='conference-paper', venue='HSCC'), pi='P', oa='W1')
    pages = dict(title=collections.defaultdict(dict, P={papers.norm_title(r['title']): (2, False)}), doi=collections.defaultdict(dict))
    kept, _ = papers.drop_not_papers([r], {'P': {papers.norm_title(r['title']): 3}}, n, pages)
    assert kept == [r] and n['single_author_abstract_kept_dblp_coauthors'] == 1
    kept, _ = papers.drop_not_papers([r], {'P': {papers.norm_title(r['title']): 1}}, n, pages)
    assert kept == [] and n['not_paper:invited_abstract'] == 1
