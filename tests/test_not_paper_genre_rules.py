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


@pytest.mark.parametrize('title,typ', [
    ('Custom Sub-Systems and Circuits for Deep Learning: Guest Editorial Overview', 'article'),
    ('Artificial Intelligence–Based Copilots to Generate Causal Evidence', 'editorial')])
def test_editorials_by_title_label_or_type(title, typ):
    assert papers.not_a_paper(row(title, typ=typ)) == 'editorial'


def test_editorial_type_switch(monkeypatch):
    monkeypatch.setattr(papers, 'EDITORIAL_TYPE_DROPS', False)
    assert papers.not_a_paper(row('Artificial Intelligence–Based Copilots to Generate Causal Evidence', typ='editorial')) is None
    assert papers.not_a_paper(row('Circuits: Guest Editorial Overview')) == 'editorial'


def test_editorial_research_titles_stay():
    assert papers.not_a_paper(row('Decisions and bias in peer review: a field study of editors')) is None


GKIOULEKAS = 'Reply to: The overwhelming role of ballistic photons in ultrasonically guided light through a scattering medium'


def test_reply_to_letters_switch_default_off(monkeypatch):
    r = row(GKIOULEKAS, typ='letter', venue='Nature Communications', byline=('A B',) * 8)
    assert papers.REPLY_TO_LETTERS_DROP is False
    assert papers.not_a_paper(r) is None
    monkeypatch.setattr(papers, 'REPLY_TO_LETTERS_DROP', True)
    assert papers.not_a_paper(r) == 'commentary'
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
def test_abstract_family_switch_default_off(monkeypatch, title, typ, venue, doi):
    r = row(title, typ=typ, venue=venue, doi=doi)
    assert papers.ABSTRACT_FAMILY_DROPS is False
    assert papers.not_a_paper(r) is None
    monkeypatch.setattr(papers, 'ABSTRACT_FAMILY_DROPS', True)
    assert papers.not_a_paper(r) == 'meeting_abstract:genre'


def test_abstract_family_keeps_papers(monkeypatch):
    monkeypatch.setattr(papers, 'ABSTRACT_FAMILY_DROPS', True)
    assert papers.not_a_paper(row('Mixed-integer programming for TSP', venue='Operations Research', doi='10.1287/opre.2020.0001')) is None
    assert papers.not_a_paper(row('Neural Machine Translation of Rare Words', typ='conference-paper', doi='10.18653/v1/P16-1162')) is None
    assert papers.not_a_paper(row('BERT', typ='article')) is None
