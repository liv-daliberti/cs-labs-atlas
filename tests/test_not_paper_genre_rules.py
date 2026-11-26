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


def test_guest_editorial_label_anywhere_in_title():
    t = 'Custom Sub-Systems and Circuits for Deep Learning: Guest Editorial Overview'
    assert papers.not_a_paper(row(t)) == 'editorial'


def test_editorial_type_switch_default_off(monkeypatch):
    r = row('Artificial Intelligence–Based Copilots to Generate Causal Evidence', typ='editorial')
    assert papers.EDITORIAL_TYPE_DROPS is False
    assert papers.not_a_paper(r) is None   # R-PAP-18: the type alone is kept
    monkeypatch.setattr(papers, 'EDITORIAL_TYPE_DROPS', True)
    assert papers.not_a_paper(r) == 'editorial'


def test_editorial_research_titles_stay():
    assert papers.not_a_paper(row('Decisions and bias in peer review: a field study of editors')) is None


GKIOULEKAS = 'Reply to: The overwhelming role of ballistic photons in ultrasonically guided light through a scattering medium'


def test_reply_to_letters_switch_on(monkeypatch):
    r = row(GKIOULEKAS, typ='letter', venue='Nature Communications', byline=('A B',) * 8)
    assert papers.REPLY_TO_LETTERS_DROP is True   # owner 2026-11-12
    assert papers.not_a_paper(r) == 'commentary'
    monkeypatch.setattr(papers, 'REPLY_TO_LETTERS_DROP', False)
    assert papers.not_a_paper(r) is None
    assert papers.not_a_paper(row('Reply Prediction for Email Threads')) is None


def test_bare_workshop_acronym_is_front_matter():
    r = row("ADVM'21", typ='conference-paper', venue='ACM International Conference on Multimedia (ACM MM)', doi='10.1145/3474085.3478572')
    assert papers.not_a_paper(r) == 'proceedings_volume'
    for t in ("Attention is all you need", "BERT'21: a replication", 'SLAM', "Transformers'"):
        assert papers.not_a_paper(row(t, typ='conference-paper')) is None


FAMILY = [
    ('Summarization of Dialogues and Conversations At Scale', 'conference-paper', None, '10.18653/v1/2023.eacl-tutorials.3'),
    ('A Food Logging System for iOS with Natural Spoken Language Meal Descriptions (P21-009-19)', 'article', 'Current Developments in Nutrition', '10.1093/cdn/nzz041.p21-009-19'),
    ('PLEURAL RETRACTION: A NEW LUNG ULTRASOUND FINDING OF INTERSTITIAL LUNG DISEASE?', 'article', 'CHEST Journal', '10.1016/j.chest.2023.07.2607'),
    ('INSIGHTS INTO THE CONTRIBUTION OF RARE NONCODING VARIATION IN AUTISM SPECTRUM DISORDER', 'article', 'European Neuropsychopharmacology', '10.1016/j.euroneuro.2019.07.073')]


@pytest.mark.parametrize('title,typ,venue,doi', FAMILY)
def test_abstract_family_switch_on(monkeypatch, title, typ, venue, doi):
    r = row(title, typ=typ, venue=venue, doi=doi)
    assert papers.ABSTRACT_FAMILY_DROPS is True   # owner 2026-11-12: the narrow patterns
    assert papers.not_a_paper(r) == 'meeting_abstract:genre'
    monkeypatch.setattr(papers, 'ABSTRACT_FAMILY_DROPS', False)
    assert papers.not_a_paper(r) is None


def test_supplement_item_doi_switch_stays_off(monkeypatch):
    r = row('Lung ultrasound in interstitial disease', venue='CHEST Journal', doi='10.1016/j.chest.2023.07.2607')
    assert papers.SUPPLEMENT_ITEM_DOI_DROPS is False
    assert papers.not_a_paper(r) is None
    monkeypatch.setattr(papers, 'SUPPLEMENT_ITEM_DOI_DROPS', True)
    assert papers.not_a_paper(r) == 'meeting_abstract:genre'


def test_abstract_family_keeps_papers():
    assert papers.not_a_paper(row('Mixed-integer programming for TSP', venue='Operations Research', doi='10.1287/opre.2020.0001')) is None
    assert papers.not_a_paper(row('Neural Machine Translation of Rare Words', typ='conference-paper', doi='10.18653/v1/P16-1162')) is None
    assert papers.not_a_paper(row('BERT', typ='article')) is None


@pytest.mark.parametrize('title,typ', [
    ('不整合な推測と1対1符号【JST・京大機械翻訳】', 'conference-paper'),
    ('Knitting Skeletons 編物衣服の成形とパターン形成のためのコンピュータ支援設計ツール【JST・京大機械翻訳】', 'article'),
])
def test_explicit_jst_kyoto_translation_record_is_not_an_original_paper(title, typ):
    assert papers.not_a_paper(dict(title=title, type=typ, doi='', byline=['A B'])) == 'machine_translation'


@pytest.mark.parametrize('title', [
    'Knitting Skeletons', '不整合な推測と1対1符号',
    'Neural Machine Translation of Rare Words', 'An analysis of JST data',
])
def test_unmarked_research_remains_eligible(title):
    assert papers.not_a_paper(dict(title=title, type='article', byline=['A B'])) is None


def test_existing_nict_translation_marker_still_excluded():
    assert papers.not_a_paper(dict(title='OpenPose【Powered by NICT】', type='article')) == 'machine_translation'
