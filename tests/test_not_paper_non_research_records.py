"""R-PAP-33 (2026-11-05, round-r2 pooled failures and the owner's abstracts decision): each pattern on the real rows that failed, and the real
papers around them stay."""
import pytest

from pihier import papers


def row(title, typ='article', venue='V', byline=('A B', 'C D'), doi='10.1/x'):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=list(byline), authorship=dict(position='middle'))


REAL = [  # (tag, row): the sample's failing rows
    ('interview', row('Interview: Chris Harrison', 'editorial', 'ACM eBooks', ['Brad A. Myers'], '10.1145/3617448.3617489')),
    ('session_introduction', row('Session Introduction: Graph Representations and Algorithms in Biomedicine', 'conference-paper', 'Pacific Symposium on Biocomputing (PSB)', doi='10.1142/9789811270611_0006')),
    ('session_introduction', row('Introduction to the Minitrack on Human-Robot Interaction and Collaboration', 'conference-paper', 'Hawaii International Conference on System Sciences', doi='10.24251/hicss.2026.075')),
    ('repository_record', row('Processed data and trained models for "HOISDF: Constraining 3D Hand-Object Pose Estimation with Global Signed Distance Fields"', 'article', None, doi='10.5281/zenodo.15076380')),
    ('presentation_only', row('3D computational imaging in scattering with light field datasets (Conference Presentation)', 'conference-paper', None, ['Laura Waller'], '10.1117/12.2207644')),
    ('presentation_only', row('List-Decodability of Structured Ensembles of Codes (Invited Talk)', 'article', 'DROPS', doi='10.4230/lipics.mfcs.2020.3')),
    ('dataset_record', row('PGE Models - PL0001 - Opal-RT format with Second-wise Net Load in MATLAB data format', 'article', None, doi='')),
    ('highlights_column', row('Big Data in Finance: Highlights from the Big Data in Finance Conference Hosted at the University of Michigan October 27-28, 2016', 'preprint', 'SSRN Electronic Journal', doi='10.2139/ssrn.3131226')),
    ('highlights_column', row('SECM 2017 Workshop Summary', 'conference-abstract', None, doi='10.1109/secm.2017.15')),
    ('column', row('Research for Practice: Technology for Underserved Communities; Personal Fabrication', 'article', 'publish.UP (University of Potsdam)', doi='10.1145/3080188')),
    ('edited_volume', row('xxAI - Beyond Explainable AI', 'conference-paper', 'Lecture notes in computer science', doi='10.1007/978-3-031-04083-2')),
    ('workshop_proposal', row('EE2: Workshop on circuits for social good', 'conference-paper', 'Digest of technical papers', doi='10.1109/isscc.2018.8310410')),
    ('workshop_proposal', row('Visualization in Data Science VDS @ KDD 2022', 'conference-paper', 'KDD', doi='10.1145/3534678.3542903')),
    ('workshop_proposal', row('KDD-2023 Workshop on Decision Intelligence and Analytics for Online Marketplaces', 'conference-abstract', 'KDD', doi='10.1145/3580305.3599202')),
]


@pytest.mark.parametrize('tag,r', REAL)
def test_R_PAP_33_failing_rows_drop(tag, r):
    assert papers.not_a_paper(r) == tag


@pytest.mark.parametrize('r', [
    row('Effective combination of pretrained models - KIT@IWSLT2022', 'conference-paper', 'IWSLT', doi='10.18653/v1/2022.iwslt-1.14'),
    row('Data Provenance Tracking for Concurrent Programs', 'article', None, doi=''),
    row('Predicting the impact of dataset composition on model performance', 'article', None, doi=''),
    row('Large-scale Cloze Test Dataset Designed by Teachers', 'article', None, doi=''),
    row('Introduction to Algorithms for Session Types', 'article', 'JACM'),
    row('Interview Study of Developers Debugging Practice', 'article', 'CHI', doi='10.1145/1'),
    row('An interview study of data scientists', 'article', 'CHI', doi='10.1145/2'),
    row('Two-Timescale Q-Learning with Function Approximation in Zero-Sum Stochastic Games', 'conference-abstract', 'ACM EC', doi='10.1145/3670865.3673491'),
    row('Chapter 3: Learning', 'conference-paper', 'Lecture notes in computer science', doi='10.1007/978-3-031-04083-2_3'),
    row('A Monograph', 'book', 'Springer', doi='10.1007/978-3-031-04083-2'),
    row('Psychology preprint', 'preprint', None, doi='10.17605/osf.io/sedn6'),
    row('Report on the Reproducibility of Deep Learning Models', 'article', 'ICML', doi='10.1/z'),
    row('A workshop on the road: field notes', 'article', 'CSCW', doi='10.1/w')])
def test_R_PAP_33_real_papers_stay(r):
    assert papers.not_a_paper(r) is None


def test_R_PAP_33_conference_abstract_by_pages():
    r = row('Some abstract', 'conference-abstract', 'ACM EC', byline=('A', 'B', 'C'), doi='10.1145/9')
    assert papers.not_a_paper(r, pages=2) == 'conference_abstract'
    assert papers.not_a_paper(r, pages=8) is None and papers.not_a_paper(r) is None


def test_R_PAP_33_conference_volume_titles():
    assert papers.not_a_paper(row('Conference on Health, Inference, and Learning (CHIL) 2022', 'article', 'CHIL', doi='')) == 'proceedings_volume'
    assert papers.not_a_paper(row('Workshop on Internet Economics (WIE2016) Final Report.', 'article', 'x', doi='')) is not None
    assert papers.not_a_paper(row('Conference on the Mathematics of Learning: A Survey', 'article', 'x', doi='10.1/q')) is None


def test_R_PAP_38_book_chapters_are_dated_by_the_original_paper():
    chapter = dict(id='https://openalex.org/W4385489965', doi='https://doi.org/10.1145/3596711.3596769', title='Video Textures', type='book-chapter', publication_year=2023,
                   publication_date='2023-06-01', primary_location=dict(source=dict(display_name='ACM eBooks', type='book series')))
    date, by = papers.venue_version_date(chapter, {papers.norm_title('Video Textures'): (2000, 'conf/siggraph/SchodlSSE00')})
    assert date == '2000' and by['venue_year'] == 2000 and by['dblp_key'] == 'conf/siggraph/SchodlSSE00'   # before 2016: dropped by the build (dated_before_window)
    article = dict(chapter, type='article')
    assert papers.venue_version_date(article, {papers.norm_title('Video Textures'): (2000, 'k')})[1] is None   # an article is not re-dated
    assert papers.venue_version_date(chapter, {})[1] is None


def test_R_PAP_39_reviewed_not_paper_records():
    p = dict(notPapers=[dict(doi='10.1631/fitee.1820000', oa='https://openalex.org/W2894741214')])
    r = dict(doi='10.1631/fitee.1820000', oa='https://openalex.org/W2894741214')
    assert papers.reviewed_not_paper(p, r) and not papers.reviewed_not_paper(p, dict(doi='10.1631/fitee.1700001', oa='x')) and not papers.reviewed_not_paper(None, r)


def test_R_PAP_39_the_georgia_tech_entry_has_evidence():
    import json
    from pathlib import Path
    f = Path(__file__).resolve().parents[1] / 'hierarchy/gatech/reviewed/census-overrides-school.json'
    e = json.loads(f.read_text())['Fumin Zhang']['not_papers'][0]
    assert e['doi'] == '10.1631/fitee.1820000' and e['why'] and len(e['evidence'][0]['sha256']) == 64


def test_R_PAP_38_a_springer_chapter_one_year_after_its_conference_is_no_reprint():
    chapter = dict(id='x', doi='https://doi.org/10.1007/978-3-319-1_5', title='Robust Adaptive Coverage for Robotic Sensor Networks', type='book-chapter',
                   publication_year=2016, publication_date='2016-03-01', primary_location=dict(source=dict(display_name='Springer tracts in advanced robotics', type='book series')))
    v = {papers.norm_title(chapter['title']): (2015, 'conf/isrr/X15')}
    assert papers.venue_version_date(chapter, v)[1] is None                              # 2016 chapter, 2015 conference: stays
    assert papers.venue_version_date(dict(chapter, publication_year=2019, publication_date='2019-03-01'), v)[1] is not None   # four years on: a reprint
