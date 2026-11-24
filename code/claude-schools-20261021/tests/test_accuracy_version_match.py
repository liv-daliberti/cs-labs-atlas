"""accuracy/version_match.py: a DBLP venue record is matched to the preprint/publisher version of the same work in the build."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('version_match', Path(__file__).resolve().parents[1] / 'accuracy' / 'version_match.py')
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


def test_same_work_other_version_is_strong():
    assert V.same_work(dict(title='LURK: Lambda, the Ultimate Recursive Knowledge.', year=2023, authors=['Nada Amin', 'John Burnham', 'Cameron Wong']),
                       dict(title='LURK: Lambda, the Ultimate Recursive Knowledge (Experience Report)', date='2023-08-30',
                            byline=['Nada Amin', 'John C. Burnham', 'Cameron Wong'])) == 'strong'
    assert V.same_work(dict(title='MLPerf Mobile Inference Benchmark: An Industry-Standard Open-Source Machine Learning Benchmark for On-Device AI.',
                            year=2022, authors=['Vijay Janapa Reddi', 'David Kanter']),
                       dict(title='MLPerf Mobile Inference Benchmark', date='2020-12-03',
                            byline=['Reddi, Vijay Janapa', 'Kanter, David', 'Mattson, Peter'])) == 'strong'


def test_retitled_version_is_only_a_candidate():
    assert V.same_work(dict(title='Connecting Federated ADMM to Bayes.', year=2025, authors=['Siddharth Swaroop', 'Mohammad Emtiyaz Khan', 'Finale Doshi-Velez']),
                       dict(title='Federated ADMM from Bayesian Duality', date='2025-06-16',
                            byline=['Möllenhoff, Thomas', 'Swaroop, Siddharth', 'Doshi-Velez, Finale', 'Khan, Mohammad Emtiyaz'])) == 'candidate'


def test_other_paper_of_the_same_authors_is_never_strong():
    # Knowles/Koehn wrote several neural-translation papers (JHU 2026-11-19): shared words alone must not count as the same work
    d = dict(title='Lightweight Word-Level Confidence Estimation for Neural Interactive Translation Prediction.', year=2018, authors=['Rebecca Knowles', 'Philipp Koehn'])
    r = dict(title='A user study of neural interactive translation prediction', date='2019-05-02', byline=['Rebecca Knowles', 'Marina Sanchez-Torron', 'Philipp Koehn'])
    assert V.same_work(d, r) != 'strong'
    assert V.same_work(d, dict(r, title='Six Challenges for Neural Machine Translation', date='2017-01-01')) != 'strong'


def test_no_match_outside_window_authors_title_or_date():
    d = dict(title='Federated ADMM Bayes', year=2025, authors=['A Swaroop', 'B Khan'])
    ok = dict(title='Federated ADMM Bayes', date='2025-01-01', byline=['Swaroop, A', 'Khan, B'])
    assert V.same_work(d, ok) == 'candidate' or V.same_work(d, ok) == 'strong'
    assert V.same_work(d, dict(ok, date='2019-01-01')) is None
    assert V.same_work(d, dict(ok, byline=['Smith, J', 'Jones, K'])) is None
    assert V.same_work(d, dict(ok, title='Graph neural networks')) is None
    assert V.same_work(d, dict(ok, date=None)) is None
