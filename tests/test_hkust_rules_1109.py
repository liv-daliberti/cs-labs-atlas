"""R-PAP-43 (HKUST admission review, owner delegated 2026-11-09): each pattern on the real HKUST rows, and real papers around them stay."""
import pytest

from pihier import papers


def row(title, typ='article', venue='V', doi='10.1/x'):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=['A B', 'C D'], authorship=dict(position='middle'))


@pytest.mark.parametrize('r,why', [
    (row('OSDI21 Artifact for "SANRAZOR: Reducing Redundant Sanitizer Checks in C/C++ Programs"', 'conference-paper', 'Zenodo (CERN European Organization for Nuclear Research)', '10.5281/zenodo.4627767'), 'artifact_deposit'),
    (row('A Message From the Editor-in-Chief', 'editorial', 'IEEE Transactions on Mobile Computing', '10.1109/tmc.2020.1'), 'editor_message'),
    (row('Message from the Industry, Systems and Apps Co-Track Co-Chairs', 'editorial', 'Proceedings/IEEE International Conference on Mobile Data Management', '10.1109/mdm.2020.2'), 'editor_message'),
    (row('Epilogue', 'book-chapter', 'Springer eBooks', '10.1007/978-3-030-1_9'), 'front_matter'),
])
def test_R_PAP_43_drops(r, why):
    assert papers.non_research_record(r) == why


@pytest.mark.parametrize('r', [
    row('Artifact for a real paper', 'article', 'Journal', '10.1109/x.1'),
    row('A Message-Passing Approach to Graph Learning', 'article', 'ICML', '10.1/m'),
    row('Epilogue: Lessons from a decade of fuzzing', 'book-chapter', 'Springer eBooks', '10.1007/978-3-1_9'),
    row('Revision Provably Reduces Sequential Computation in Diffusion Language Models', 'preprint', 'Zenodo (CERN)', '10.5281/zenodo.23105364'),
])
def test_R_PAP_43_real_papers_stay(r):
    assert papers.non_research_record(r) is None


def test_R_PAP_33_interview_suffix_titles_drop_and_real_titles_stay():
    assert papers.non_research_record(row('Connecting minds and machines: an interview with Miguel Nicolelis', 'article', 'Journal', '10.1088/x.1')) == 'interview'
    assert papers.non_research_record(row('Semi-structured interviews in HCI: a methods study of 30 designers', 'article', 'Journal', '10.1088/x.2')) is None
