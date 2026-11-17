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
    ('conference_report', row('ACM Creativity and Cognition Conference 2017', 'article', 'IEEE Multimedia', ['Aisling Kelliher'], '10.1109/mmul.2017.4031310')),
    ('column', row('Research for Practice: Technology for Underserved Communities; Personal Fabrication', 'article', 'publish.UP (University of Potsdam)', doi='10.1145/3080188')),
    ('edited_volume', row('xxAI - Beyond Explainable AI', 'conference-paper', 'Lecture notes in computer science', doi='10.1007/978-3-031-04083-2')),
    ('workshop_proposal', row('EE2: Workshop on circuits for social good', 'conference-paper', 'Digest of technical papers', doi='10.1109/isscc.2018.8310410')),
    ('workshop_proposal', row('Visualization in Data Science VDS @ KDD 2022', 'conference-paper', 'KDD', doi='10.1145/3534678.3542903')),
    ('workshop_proposal', row('KDD-2023 Workshop on Decision Intelligence and Analytics for Online Marketplaces', 'conference-abstract', 'KDD', doi='10.1145/3580305.3599202')),
]


@pytest.mark.parametrize('tag,r', REAL)
def test_R_PAP_33_failing_rows_drop(tag, r):
    assert papers.not_a_paper(r) == tag


@pytest.mark.parametrize('landing', [
    'http://cidrdb.org/cidr2017/gongshow/abstracts/cidr2017_64.pdf',
    'https://www.cidrdb.org/cidr2025/gongshow/abstracts/another.pdf',
    'http://ui.adsabs.harvard.edu/abs/2019APS..MARR29006B/abstract',
    'https://adsabs.harvard.edu/abs/2019APS..MARX15008C/abstract',
])
def test_R_PAP_19_abstract_source_paths_override_article_or_paper_type(landing):
    r = dict(row('An ordinary research-like title', typ='article'), landing=landing)
    assert papers.not_a_paper(r) == 'meeting_abstract:source'
    r['type'] = 'conference-paper'
    assert papers.not_a_paper(r) == 'meeting_abstract:source'


@pytest.mark.parametrize('landing', [
    'https://cidrdb.org/cidr2017/papers/p64.pdf',
    'https://ui.adsabs.harvard.edu/abs/2019PhRvL.12345678A/abstract',
    'https://example.org/cidr2017/gongshow/abstracts/paper.pdf',
    'https://ui.adsabs.harvard.edu.example.org/abs/2019APS..MARR29006B/abstract',
])
def test_R_PAP_19_regular_papers_and_unrelated_hosts_stay(landing):
    assert papers.not_a_paper(dict(row('A complete research paper'), landing=landing)) is None


@pytest.mark.parametrize('title', [
    'Session 9 Overview: ML Processors From Cloud to Edge',
    'Session 1 overview: Plenary Session',
])
def test_R_PAP_33_numbered_session_overviews_are_introductions(title):
    assert papers.not_a_paper(row(title, 'conference-paper')) == 'session_introduction'
    assert papers.not_a_paper(row('Overview of a new processor architecture', 'conference-paper')) is None
    assert papers.not_a_paper(row('Session 9: a new processor architecture', 'conference-paper')) is None


def test_R_PAP_46_short_acronym_workshop_announcement():
    r = row('KDD workshop on Evaluation and Trustworthiness of Generative AI Models',
            'conference-paper', 'KDD', doi='10.1145/3637528.3671481')
    assert papers.not_a_paper(r, pages=2) == 'workshop_proposal'
    assert papers.not_a_paper(r) == 'workshop_proposal'  # OpenAlex has no page count for this record
    assert papers.not_a_paper(r, pages=10) is None


def test_issue_welcome_is_editorial_not_research():
    r = row('Welcome to AI Matters 9(3)', 'article', 'AI Matters',
            ['Ziyu Yao', 'Anuj Karpatne'], '10.1145/3626487.3626488')
    assert papers.not_a_paper(r) == 'editorial'
    assert papers.not_a_paper(row('Welcome to robust machine learning', 'article', 'AI Matters')) is None


@pytest.mark.parametrize('r', [
    row('Effective combination of pretrained models - KIT@IWSLT2022', 'conference-paper', 'IWSLT', doi='10.18653/v1/2022.iwslt-1.14'),
    row('Data Provenance Tracking for Concurrent Programs', 'article', None, doi=''),
    row('Predicting the impact of dataset composition on model performance', 'article', None, doi=''),
    row('Large-scale Cloze Test Dataset Designed by Teachers', 'article', None, doi=''),
    row('Introduction to Algorithms for Session Types', 'article', 'JACM'),
    row('The Principle of Least Action: History and Physics', 'article', None, byline=('Alberto Rojo', 'Anthony Bloch'), doi='10.1017/9781139021029'),
    row('Interview Study of Developers Debugging Practice', 'article', 'CHI', doi='10.1145/1'),
    row('An interview study of data scientists', 'article', 'CHI', doi='10.1145/2'),
    row('Two-Timescale Q-Learning with Function Approximation in Zero-Sum Stochastic Games', 'conference-abstract', 'ACM EC', doi='10.1145/3670865.3673491'),
    row('Chapter 3: Learning', 'conference-paper', 'Lecture notes in computer science', doi='10.1007/978-3-031-04083-2_3'),
    row('A Monograph', 'book', 'Springer', doi='10.1007/978-3-031-04083-2'),
    row('Psychology preprint', 'preprint', None, doi='10.17605/osf.io/sedn6'),
    row('Report on the Reproducibility of Deep Learning Models', 'article', 'ICML', doi='10.1/z'),
    row('ACM Creativity and Cognition Conference 2017: Research Findings', 'article', 'IEEE Multimedia', doi='10.1/research'),
    row('A workshop on the road: field notes', 'article', 'CSCW', doi='10.1/w')])
def test_R_PAP_33_real_papers_stay(r):
    assert papers.not_a_paper(r) is None


def test_R_PAP_33_conference_abstract_by_pages():
    r = row('Some abstract', 'conference-abstract', 'ACM EC', byline=('A', 'B', 'C'), doi='10.1145/9')
    assert papers.not_a_paper(r, pages=2) == 'conference_abstract'
    assert papers.not_a_paper(r, pages=8) is None and papers.not_a_paper(r) is None


def test_oxford_cardiovascular_research_poster_abstract_is_not_a_paper():
    poster = row('P503 Inter-subject variability explains juxtaposed effects in pharmacological treatments',
                 'conference-abstract', 'Cardiovascular Research',
                 doi='10.1093/cvr/cvy060.360')
    article = row('In silico predictions of drug-induced changes on cardiac contractility',
                  'article', 'Cardiovascular Research', doi='10.1093/cvr/cvy060')
    assert papers.not_a_paper(poster) == 'meeting_abstract:journal'
    assert papers.not_a_paper(article) is None


def test_publisher_removal_notice_is_not_original_research():
    notice = row('Notice of Removal: A Hybrid Deep Learning Architecture for Privacy-Preserving Mobile Analytics',
                 'article', 'IEEE Internet of Things Journal', doi='10.1109/jiot.2020.2967734')
    paper = row('A Hybrid Deep Learning Architecture for Privacy-Preserving Mobile Analytics',
                'article', 'IEEE Internet of Things Journal', doi='10.1109/jiot.2019.123')
    assert papers.not_a_paper(notice) == 'removal_notice'
    assert papers.not_a_paper(paper) is None


def test_oxford_bcs_heart_supplement_abstract_is_not_a_paper():
    abstract = row('69 The relationship between troponin level and mortality',
                   'conference-abstract', 'Interventional Cardiology',
                   doi='10.1136/heartjnl-2019-bcs.67')
    ordinary = row('Clinical determinants of plasma cardiac biomarkers',
                   'article', 'Heart', doi='10.1136/heartjnl-2019-314892')
    assert papers.not_a_paper(abstract) == 'meeting_abstract:congress'
    assert papers.not_a_paper(ordinary) is None


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


def test_named_repository_dataset_with_venue_is_not_a_paper():
    title = 'STARCOP dataset: Semantic Segmentation of Methane Plumes with Hyperspectral Machine Learning Models'
    assert papers.not_a_paper(row(title, venue='Zenodo', doi='10.5281/zenodo.7863342')) == 'dataset_record'
    assert papers.not_a_paper(row('Benchmark dataset: measurements', venue='figshare', doi='10.6084/m9.figshare.123')) == 'dataset_record'
    assert papers.not_a_paper(row('Dataset for methane detection', venue='Dryad', doi='10.5061/dryad.123')) == 'dataset_record'
    # A research paper describing a dataset, and repository preprints, still need normal paper review.
    assert papers.not_a_paper(row(title, venue='Scientific Data', doi='10.1038/s41597-1')) is None
    assert papers.not_a_paper(row(title, venue='Scientific Data', doi='10.5281/zenodo.7863342')) is None
    assert papers.not_a_paper(row('Learning from datasets', venue='Zenodo', doi='10.5281/zenodo.9')) is None


def test_explicit_abstract_reprint_is_not_the_full_research_paper():
    title = 'Learning to Resolve Social Dilemmas: A Survey (Abstract Reprint)'
    assert papers.not_a_paper(row(title, typ='conference-abstract', venue=None, doi='10.24963/ijcai.2024/949')) == 'conference_abstract'
    assert papers.not_a_paper(row(title, typ='article', venue='IJCAI')) == 'conference_abstract'
    assert papers.not_a_paper(row('Learning to Resolve Social Dilemmas: A Survey', typ='article', venue='JAIR')) is None
    assert papers.not_a_paper(row('Abstract Reprint Detection using Language Models', venue='ACL')) is None


@pytest.mark.parametrize('title,doi', [
    ('0182 INFLUENCE OF WEEKLY SLEEP REGULARITY ON SELF-REPORTED WELLBEING', '10.1093/sleepj/zsx050.181'),
    ('0795 IMPORTANCE OF SLEEP DATA IN PREDICTING NEXT-DAY STRESS, HAPPINESS, AND HEALTH IN COLLEGE STUDENTS', '10.1093/sleepj/zsx050.794'),
])
def test_sleep_2017_numbered_abstract_supplement(title, doi):
    assert papers.not_a_paper(row(title, venue='SLEEP', doi=doi)) == 'supplement_abstract'
    assert papers.not_a_paper(row(title[5:], venue='SLEEP', doi=doi)) is None
    assert papers.not_a_paper(row(title, venue='SLEEP', doi='10.1093/sleep/zsx050')) is None
    assert papers.not_a_paper(row(title, venue='Journal X', doi=doi)) is None
    assert papers.not_a_paper(row(title, typ='book-chapter', venue='SLEEP', doi=doi)) is None


@pytest.mark.parametrize('title,venue,doi', [
    ('2038 Restoration of Proprioception Function', 'Neurosurgery', '10.1227/neu.0000000000003360_2038'),
    ('S764 Applying Machine Learning to Large Databases', 'The American Journal of Gastroenterology', '10.14309/01.ajg.0000776588.94571.42'),
    ('310: Toward real-time ultrasound-based monitoring', 'ASAIO Journal', '10.1097/01.mat.0001279064.00604.e8'),
])
def test_clinical_program_abstract_requires_corresponding_source_signals(title, venue, doi):
    assert papers.not_a_paper(row(title, typ='conference-abstract', venue=venue, doi=doi)) == 'meeting_abstract:congress'
    assert papers.not_a_paper(row(title, venue=venue, doi=doi)) is None
    assert papers.not_a_paper(row(title, typ='conference-abstract', venue='Journal X', doi=doi)) is None
    assert papers.not_a_paper(row(title, typ='conference-abstract', venue=venue, doi='10.1/research')) is None
    assert papers.not_a_paper(row('A full study of neural interfaces', typ='conference-abstract', venue=venue, doi=doi)) is None


def test_neurosurgery_program_number_must_equal_the_doi_suffix():
    assert papers.not_a_paper(row('2039 Restoration of Proprioception Function', typ='conference-abstract',
                                 venue='Neurosurgery', doi='10.1227/neu.0000000000003360_2038')) is None


@pytest.mark.parametrize('doi', ['10.1136/lupus-2021-lupus21century.99', '10.1136/jitc-2022-sitc2022.0916'])
def test_explicit_bmj_clinical_congress_doi_family(doi):
    assert papers.not_a_paper(row('A congress programme item', doi=doi)) == 'meeting_abstract:congress'
    assert papers.not_a_paper(row('A full clinical research study', doi='10.1136/lupus-2021-000123')) is None
    assert papers.not_a_paper(row('A full clinical research study', doi='10.1136/jitc-2022-000123')) is None


def test_programme_and_cover_notices_do_not_exclude_research_about_these_topics():
    assert papers.not_a_paper(row('IMS2021 Panel Sessions', venue='IEEE Microwave Magazine')) == 'session_introduction'
    assert papers.not_a_paper(row('Cover Image, Volume 40, Number 8, December 2023')) == 'cover_image'
    assert papers.not_a_paper(row('Learning from Panel Sessions', venue='Journal X')) is None
    assert papers.not_a_paper(row('IMS2021 Panel Sessions: A quantitative study', venue='Journal X')) is None
    assert papers.not_a_paper(row('Cover Image Retrieval for Scientific Documents')) is None


@pytest.mark.parametrize('title', ['Correction to Analyzing Learned Molecular Representations for Property Prediction',
                                  'Corrections to "LOCUS: A Multi-Sensor Lidar-Centric Solution"'])
def test_correction_notice_does_not_require_a_colon(title):
    assert papers.not_a_paper(row(title)) == 'erratum'
    assert papers.not_a_paper(row('Correction of selection bias in learned representations')) is None
    assert papers.not_a_paper(row('Correcting errors in wireless signals')) is None
