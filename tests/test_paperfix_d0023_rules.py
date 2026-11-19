"""D-0023 (2026-11-19): gate-9 pi2 Toronto precision and ZJU coverage rules, R-PAP-48 .. R-PAP-53."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools' / 'pihier'))
import pi_hierarchy as h  # noqa: E402
import pi_fulltext_affiliation as F  # noqa: E402


def row(**kw):
    base = dict(title='A study', venue='Some Journal', type='article', doi='', byline=['A', 'B', 'C'], authorship={'position': 'middle'})
    base.update(kw)
    return base


def test_R_PAP_48_oup_supplement_doi_is_a_meeting_abstract():
    r = row(title='A15 CX3CR1+ MYELOID CELL-INTRINSIC NOD2 SIGNALING', doi='10.1093/jcag/gwaf042.015', venue='Journal of the Canadian Association of Gastroenterology')
    assert h.not_a_paper(r) == 'meeting_abstract:supplement'
    assert h.not_a_paper(row(doi='10.1093/eurheartj/ehz748.0574')) == 'meeting_abstract:supplement'
    assert h.not_a_paper(row(doi='10.1093/ofid/ofx163.110', type='conference-abstract')) == 'meeting_abstract:supplement'
    # ordinary OUP articles have no dotted item suffix; other types are untouched
    assert h.not_a_paper(row(doi='10.1093/bioinformatics/btab123')) is None
    assert h.not_a_paper(row(doi='10.1093/nar/gkab1112')) is None
    assert h.not_a_paper(row(doi='10.1093/jcag/gwaf042.015', type='book-chapter')) is None


def test_R_PAP_48_neuromuscular_disorders_congress_items():
    r = row(title='The natural history of nemaline myopathy', venue='Neuromuscular Disorders', doi='10.1016/j.nmd.2017.06.320')
    assert h.not_a_paper(r) == 'meeting_abstract:supplement'
    assert h.not_a_paper(row(venue='Neuromuscular Disorders', doi='10.1016/j.nmd.2019.05.012')) is None   # a regular item number below 100
    assert h.not_a_paper(row(doi='10.1016/j.neuron.2019.01.320')) is None                                  # other journals untouched


def test_R_PAP_49_dagstuhl_artifact_deposit():
    r = row(title='Travelling Salesperson Problem with Self Deleting Graphs', doi='10.4230/artifacts.23555', venue='DROPS (Schloss Dagstuhl)')
    assert h.not_a_paper(r) == 'artifact_deposit'
    assert h.not_a_paper(row(doi='10.4230/lipics.cp.2024.12')) is None
    assert h.not_a_paper(row(doi='10.4230/lipics.cp.2024.12', title='Artifact evaluation methods')) is None


def test_R_PAP_50_workshop_ordinal_front_matter():
    for t in ("Meta-HCI: First Workshop on Meta-Research in HCI", "ADVM'21: 1st International Workshop on Adversarial Learning for Multimedia",
              "DRL4IR: 2nd Workshop on Deep Reinforcement Learning for Information Retrieval", "WIKI’2022: 9th Annual Wiki Workshop"):
        assert h.not_a_paper(row(title=t, type='conference-paper')) == 'workshop_proposal', t
    assert h.not_a_paper(row(title="Meta-HCI: First Workshop on Meta-Research in HCI", type='article')) is None   # conference records only
    for t in ('Lessons from the first workshop on federated learning: a case study of data', 'A new method for X: the second approach to Y',
              'Graph coloring: First results on a workshop scheduling problem'):
        assert h.not_a_paper(row(title=t, type='conference-paper')) is None, t


def test_R_PAP_51_journal_state_report():
    t = 'Report on the state and changes of the SoSyM journal (2025 summary)'
    assert h.not_a_paper(row(title=t)) == 'editorial'
    assert h.not_a_paper(row(title='Report on the state of the art in graph neural networks')) is None
    assert h.not_a_paper(row(title='Report on the state of the art of a journal recommender system')) is None
    assert h.not_a_paper(row(title='Report on the state and changes of the field of graph learning')) is None


FLEET_PAGE = ('Monocular Depth Estimation using Diffusion Models\n\nSaurabh Saxena 1 Abhishek Kar 1 Mohammad Norouzi 1 David J. Fleet 1\n\n'
              'arXiv:2302.14816v1 [cs.CV] 28 Feb 2023\n\nAbstract\nWe formulate monocular depth estimation using\ndenoising diffusion models.\n\n'
              '1. Introduction\nDiffusion models are good. First, much of the existing data is noisy\n1\nGoogle Research. Correspondence to: Saurabh Saxena\n<srbs@google.com>.\n\nand incomplete.\n')


def test_R_PAP_52_page1_company_footnote_places_the_paper_elsewhere():
    names = ['Saurabh Saxena', 'Mohammad Norouzi', 'David J. Fleet']
    assert h.page1_elsewhere('ok_absent', FLEET_PAGE, 'toronto', 'Monocular Depth Estimation using Diffusion Models', names) == 'Google Research'
    # the school named anywhere on the page keeps the paper; a page that does not carry a byline marker is unchanged
    assert h.page1_elsewhere('ok_absent', FLEET_PAGE.replace('Google Research', 'Google Research, University of Toronto'), 'toronto', None, names) is None
    assert h.page1_elsewhere('ok_absent', FLEET_PAGE.replace('1 Mohammad', 'Mohammad').replace('1 David J. Fleet 1', 'David J. Fleet'), 'toronto', None, ['Mohammad Norouzi']) is None


ONEPOSE_PAGE = ('OnePose++: Keypoint-Free One-Shot Object Pose\nEstimation without CAD Models\n\narXiv:2301.07673v1 [cs.CV] 18 Jan 2023\n\n'
                'Xingyi He1∗\n\n1\n\nZhejiang University\n\nJiaming Sun2∗\nHujun Bao1\n2\nYuang Wang1\nDi Huang3\n1†\nXiaowei Zhou\n\n'
                'Image Derivative Inc.\n\n3\n\nThe University of Sydney\n\nAbstract\nWe propose a new method for object pose estimation.\n')


def test_R_PAP_53_grid_author_block_affiliation_ahead_of_the_name():
    import tomli as toml
    with open(Path(__file__).resolve().parent.parent / 'schools' / 'zju.toml', 'rb') as f:
        aff = re.compile(toml.load(f)['affiliation']['regex'], re.I)
    how, quotes = F.tie(ONEPOSE_PAGE, [('hujun', 'bao')], aff)
    assert how == 'marker' and any('Zhejiang University' in q for q in quotes)
    # an author whose marker names another institution is not tied
    assert F.tie(ONEPOSE_PAGE, [('jiaming', 'sun')], aff)[0] is None
    assert F.tie(ONEPOSE_PAGE, [('di', 'huang')], aff)[0] is None


def test_R_PAP_54_zju_cadcg_key_lab_is_zju():
    import tomli as toml
    with open(Path(__file__).resolve().parent.parent / 'schools' / 'zju.toml', 'rb') as f:
        aff = re.compile(toml.load(f)['affiliation']['regex'], re.I)
    for s in ('State Key Lab of CAD&#x0026;CG', 'State Key Laboratory of CAD and CG, Hangzhou, China', 'State Key Lab of CAD&CG', '计算机辅助设计与图形系统国家重点实验室'):
        assert aff.search(s), s
    for s in ('State Key Laboratory of Industrial Control Technology', 'Zhejiang Lab', 'CAD Lab, Hangzhou Dianzi University'):
        assert not aff.search(s), s


def test_R_PAP_39_toronto_d0023_reviewed_not_papers():
    import json
    d = json.loads((Path(__file__).resolve().parent.parent / 'hierarchy/toronto/reviewed/census-overrides-school.json').read_text())
    for pi, doi in (('Gerald Penn', '10.1145/3170427.3170660'), ('Elias B. Khalil', '10.1609/aaai.v37i13.26810'), ('Scott Sanner', '10.1145/3726302.3730369')):
        e = d[pi]['not_papers'][0]
        assert e['doi'] == doi and e['why'] and len(e['evidence'][0]['sha256']) == 64 and e['evidence'][0]['quote']
        assert h.reviewed_not_paper(dict(notPapers=d[pi]['not_papers']), dict(doi=doi, oa=e['oa']))
