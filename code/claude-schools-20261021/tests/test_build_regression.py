"""tools/build_regression.py thresholds on synthetic counts."""
import build_regression as br


def snap(lab_papers, per_pi, digest='d'):
    rows = dict(lab_papers=lab_papers, student_papers=100, lab_student_pairs=50, pis=len(per_pi))
    return dict(at='t', source='s', code='c', schools={'princeton': dict(
        builtAt='b', report=dict(lab_papers=lab_papers, students=40), rows=rows,
        digests=dict(lab_papers=digest, student_papers='x', students='y', pis='z'), per_pi=per_pi)})


def kinds(res):
    return sorted((f['kind'], f.get('pi') or f.get('count')) for f in res['flags'])


def test_identical_build_has_no_flags():
    res = br.compare(snap(1000, {'A': 100, 'B': 5}), snap(1000, {'A': 100, 'B': 5}))
    assert res['flags'] == [] and all(res['schools']['princeton']['identical'].values())


def test_school_swing_over_five_percent():
    res = br.compare(snap(1000, {'A': 100}), snap(1060, {'A': 100}))
    assert ('school_count', 'lab_papers') in kinds(res) and ('school_rows', 'lab_papers') in kinds(res)
    assert br.compare(snap(1000, {'A': 100}), snap(1040, {'A': 100}))['flags'] == []


def test_pi_loss_and_gain_thresholds():
    before = {'Loses': 40, 'SmallLoss': 12, 'Gains': 15, 'SmallGain': 5, 'Gone': 10, 'Tiny': 3}
    after = {'Loses': 25, 'SmallLoss': 4, 'Gains': 40, 'SmallGain': 20, 'Tiny': 0, 'New': 25}
    res = br.compare(snap(1000, before), snap(1000, after))
    assert kinds(res) == [('pi_gain', 'Gains'), ('pi_loss', 'Loses'), ('pi_new', 'New'), ('pi_vanished', 'Gone')]
    # SmallLoss loses 8 (< 10), SmallGain gains 15 (< 20), Tiny loses 3: not flagged
