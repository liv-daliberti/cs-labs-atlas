"""AI-dose detector-free cross-checks (ai-writing/dose/excess.py) on synthetic documents."""
import numpy as np

import excess as E


def docs(rng, n, marker_p):
    base = [f'w{i}' for i in range(300)]
    out = []
    for _ in range(n):
        toks = [base[j] for j in rng.integers(0, 300, 60)]
        toks += [f'm{j}' for j in range(20) if rng.random() < marker_p]
        out.append(toks)
    return out


def test_kobak_rate():
    assert E.kobak_rate('Delve into the intricate tapestry', {'delve', 'intricate'}) == 400.0
    assert np.isnan(E.kobak_rate('', {'x'}))


def test_vocab_and_matrix():
    d = [['a', 'b', 'a'], ['b', 'c'], ['b']]
    v = E.build_vocab(d, size=2, min_df=1)
    assert list(v) == ['b', 'a']
    X = E.occurrence_matrix(d, v)
    assert X.toarray().tolist() == [[1, 1], [1, 0], [1, 0]]


def test_liang_recovers_the_mixture():
    rng = np.random.default_rng(1)
    h_tr, l_tr = docs(rng, 600, 0.02), docs(rng, 600, 0.5)
    vocab = E.build_vocab(h_tr + l_tr, size=400, min_df=3)
    m = E.LiangMixture(E.occurrence_matrix(h_tr, vocab), E.occurrence_matrix(l_tr, vocab))
    h_te, l_te = docs(rng, 600, 0.02), docs(rng, 600, 0.5)
    Xh, Xl = E.occurrence_matrix(h_te, vocab), E.occurrence_matrix(l_te, vocab)
    cal = dict(E.calibration(m, Xh, Xl, alphas=(0, .25, .5, 1.0), n=800))
    assert cal[0] < 0.05 and abs(cal[.25] - .25) < .07 and abs(cal[.5] - .5) < .08 and cal[1.0] > .93
    a, lo, hi = m.estimate(Xh, boot=30)
    assert a < 0.05 and lo <= a <= hi + 1e-9
