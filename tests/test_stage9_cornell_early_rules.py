import re
from pihier import papers

AFF = re.compile(r'cornell univ', re.I)


def row(**k):
    return dict(dict(title='A real paper', venue='X', type='article', doi='10.1/x', byline=['a', 'b']), **k)


def test_chairs_welcome_title_is_editorial():
    for t in ('CSCW 2018: Chairs’ welcome', "Chairs' Welcome", 'Message from the Program Chairs', 'Welcome message from the general chairs', 'Program Chairs’ Message'):
        assert papers.not_a_paper(row(title=t, type='conference-paper', doi='')) == 'editorial', t
    assert papers.not_a_paper(row(title='How chairs welcome newcomers: a study of program committees')) is None


def test_R_PAP_64_iovs_without_doi_is_meeting_abstract_but_with_doi_is_not():
    v = 'Investigative Ophthalmology & Visual Science'
    assert str(papers.not_a_paper(row(title='Understanding AI visual aids', venue=v, doi=''))).startswith('meeting_abstract')
    assert papers.not_a_paper(row(title='Understanding AI visual aids', venue=v, doi='10.1167/iovs.61.1.1')) is None


def test_R_PAP_62_work_done_elsewhere_overrides_the_listed_affiliation():
    assert papers.work_done_elsewhere(['Cornell (work done at MIT), Ithaca, NY, USA'], AFF)
    assert papers.work_done_elsewhere(['Cornell University. This work was done while at Google'], AFF)
    assert not papers.work_done_elsewhere(['Cornell University, Ithaca'], AFF)
    assert not papers.work_done_elsewhere(['Cornell University (work done at Cornell University)'], AFF)
    assert not papers.work_done_elsewhere(['Cornell University (work done at MIT)', 'Department of Computer Science, Cornell University'], AFF)
