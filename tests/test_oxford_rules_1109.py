"""Oxford admission-review rules of 2026-11-09 (owner delegated the choices to Claude): R-PAP-19 congress supplements, R-PAP-33
repository deliverables, R-PAP-41 source-title guard. Each pattern on the real Oxford rows that failed, and the real papers around them stay."""
import pytest

import source_title_guard as g
from pihier import papers


def row(title, typ='article', venue='V', doi='10.1/x', byline=('A B', 'C D')):
    return dict(title=title, type=typ, venue=venue, doi=doi, byline=list(byline), authorship=dict(position='middle'))


@pytest.mark.parametrize('r', [
    row('PO222 / #1008 A SYSTEM FOR INVESTIGATING BIOELECTRONIC THERAPIES USING A MULTICONTACT NERVE CUFF', 'conference-abstract', 'Neuromodulation Technology at the Neural Interface', '10.1016/j.neurom.2022.08.394'),
    row('O025 FIRST-IN-MAN TRIAL OF PEDUNCULOPONTINE REGION DEEP BRAIN STIMULATION', 'article', 'Neuromodulation', '10.1016/j.neurom.2024.09.126'),
    row('RF006 EPIONE: EFFICACY OF PAIN INTERVENTION USING DBS NEUROMODULATION', 'article', 'Neuromodulation', '10.1016/j.neurom.2025.09.286'),
    row('ID: 324641 Patient Controller Protocol for Blinded Trials of Neuromodulation', 'article', 'Neuromodulation Technology at the Neural Interface', '10.1016/j.neurom.2024.06.069'),
    row('Gas-exchange and ventilation imaging of COPD in comparison to a healthy cohort using hyperpolarized Xenon-129 MRI', 'article', 'European Respiratory Journal', '10.1183/13993003.congress-2019.oa1918'),
    row('The evaluation of frequency dependence of resistance', 'article', 'ERJ', '10.1183/1393003.congress-2017.pa2476'),
])
def test_R_PAP_19_congress_supplements_drop(r):
    assert papers.not_a_paper(r) == 'meeting_abstract:congress'


@pytest.mark.parametrize('r', [
    row('Closed-loop deep brain stimulation for essential tremor: a randomized trial', 'article', 'Neuromodulation', '10.1016/j.neurom.2023.04.003'),
    row('Neurophysiologic Biomarkers of Invasive Neuromodulation Therapy for Epilepsy', 'article', 'Neuromodulation Technology at the Neural Interface', '10.1016/j.neurom.2026.01.004'),
    row('Spinal cord stimulation and chronic pain outcomes', 'article', 'Neuromodulation', '10.1016/j.neurom.2022.10.045'),
    row('Deep learning for COPD detection', 'article', 'European Respiratory Journal', '10.1183/13993003.01234-2020'),
    row('A paper from another Elsevier journal', 'article', 'Brain Stimulation', '10.1016/j.brs.2023.01.001'),
])
def test_R_PAP_19_real_articles_stay(r):
    assert papers.not_a_paper(r) is None


@pytest.mark.parametrize('title,typ', [
    ('D2.5 FAIRplus FAIR Data Maturity Framework', 'report'),
    ('D2.1 FAIR Cookbook', 'article'),
    ('SMASH-HCM D1.4 Risk Assessment Reports', 'article'),
    ('BY-COVID D3.3.2 COVID-19 Data Portal', 'article'),
    ('M5: Preliminary Analysis Results', 'article'),
    ('BioFAIR Final Report', 'report'),
    ('Response of the FAIRsharing Community to the OSTP RFI on "Desirable Characteristics of Repositories"', 'report'),
    ('Building Resilient Data Science Programs', 'report'),
    ('FAIRplus Deliverable 5.8: FAIRplus overview of the scientific publications', 'report'),
])
def test_R_PAP_33_zenodo_deliverables_drop(title, typ):
    r = row(title, typ, 'Zenodo (CERN European Organization for Nuclear Research)', '10.5281/zenodo.123456')
    assert papers.not_a_paper(r) == 'repository_deliverable'


@pytest.mark.parametrize('title,typ', [
    ('FAIRsharing, a FAIR-enabling service for repositories, standards and policies', 'article'),
    ('Adversarial Robustness Guarantees for Classification with Gaussian Processes', 'conference-paper'),
    ('Digital Music Objects: Research Objects For Music', 'conference-paper'),
    ('Data Repository Selection: Criteria That Matter', 'article'),
])
def test_R_PAP_33_zenodo_publications_stay(title, typ):
    r = row(title, typ, 'Zenodo (CERN European Organization for Nuclear Research)', '10.5281/zenodo.123456')
    assert papers.not_a_paper(r) is None


def test_R_PAP_33_deliverable_pattern_only_on_repository_dois():
    assert papers.not_a_paper(row('D2.5 A real conference paper title', 'conference-paper', 'ICML', '10.1145/1')) is None
    assert papers.not_a_paper(row('Annual Report on Learning', 'article', 'JMLR', '10.1145/2')) is None


@pytest.mark.parametrize('a,b', [
    ('Progress & Compress: A scalable framework for continual learning', 'Progress &amp; Compress: A scalable framework for continual learning'),
    ('Iterate Averaging in the Quest for Best Test Error', 'Iterative Averaging in the Quest for Best Test Error'),
    ('AnACor2.0 : a GPU-accelerated software', '<i>AnACor2.0</i> : a GPU-accelerated software'),
    ('Hyperpolarized 129Xe MRI Abnormalities in Dyspneic Patients', 'Hyperpolarized <sup>129</sup>Xe MRI Abnormalities in Dyspneic Patients'),
    ('Mosquito Detection with Neural Networks', 'Mosquito Detection with Neural Networks: The Buzz of Deep Learning'),
    ('Salt & Pepper Heatmaps', 'SALT AND PEPPER HEATMAPS'),
])
def test_R_PAP_41_tolerant_matches(a, b):
    assert g.titles_match(a, b)


@pytest.mark.parametrize('rec,src', [
    ('HumBugDB: a large-scale acoustic mosquito dataset', 'Mosquito Detection with Neural Networks: The Buzz of Deep Learning'),
    ('Dynamic / ME-JEPA v2.0.0-rc1: Audited World-Model Runtime', 'The Curse of Recursion: Training on Generated Data Makes Models Forget'),
])
def test_R_PAP_41_corrupted_records_hold(rec, src):
    sources = {'1705.05180': {'title': src}, '2305.17493': [src]}
    r = dict(pi='X', doi='10.48550/arxiv.1705.05180v2' if 'Hum' in rec else '10.48550/arxiv.2305.17493', title=rec)
    assert g.title_conflict(r, sources) == [src]
    assert g.held_rows([r], sources)[0]['verdict'] == 'hold'


def test_R_PAP_41_unknown_doi_is_not_judged_and_any_version_title_matches():
    assert g.title_conflict(dict(doi='10.1/none', title='Anything'), {}) is None
    s = {'10.1109/x': ['Old Title of the Paper', 'New Title of the Paper']}
    assert g.title_conflict(dict(doi='10.1109/X', title='Old title of the paper.'), s) is None


def test_R_HIER_05_computing_as_object_people_are_never_accepted():
    """The five Oxford Internet Institute people excluded as a class (owner delegated to Claude 2026-11-09) are held or excluded, never accepted as PIs."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    names = ['Gina Neff', 'Luciano Floridi', 'Mariarosaria Taddeo', 'Sandra Wachter', 'Bernie Hogan']
    text = (root / 'docs' / 'RULES.md').read_text()
    section = text.split('### R-HIER-05', 1)[1].split('\n### ', 1)[0]
    assert all(n in section for n in names) and 'excluded_scope' in section
    p = root / 'hierarchy' / 'oxford' / 'reviewed' / 'cs-related-review.json'
    if p.exists():
        decisions = {d['name']: d['decision'] for d in json.loads(p.read_text())['decisions']}
        assert all(decisions.get(n, 'excluded_scope') in ('held_scope', 'excluded_scope') for n in names)
