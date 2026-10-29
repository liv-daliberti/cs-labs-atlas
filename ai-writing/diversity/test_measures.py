"""Unit tests for measures.py on toy data. Run: python test_measures.py (or pytest, where installed)."""
import math, random, string, sys
import numpy as np
import measures as M

rng = np.random.default_rng(1)


def unit(X):
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


# ---------------- semantic

def test_identical_vectors_are_minimum_diversity():
    U = unit(np.tile(rng.normal(size=(1, 32)), (6, 1)))
    assert close(M.extent(U), 0) and close(M.dispersion(U), 0)
    assert close(M.pairwise_distance(U), 0, 1e-6)
    assert close(M.vendi(U), 1.0, 1e-6)


def test_vendi_equals_k_for_orthogonal():
    for k in (2, 5, 9):
        U = np.eye(16)[:k]
        assert close(M.vendi(U), k, 1e-9)
        assert close(M.pairwise_distance(U), 1.0)


def test_gram_forms_agree_with_direct():
    U = unit(rng.normal(size=(12, 20)))
    g = M.gram_measures(U @ U.T)
    assert close(g['S1'], M.extent(U)) and close(g['S2'], M.dispersion(U))
    assert close(g['S3'], M.pairwise_distance(U)) and close(g['S4'], M.vendi(U))


def test_more_spread_set_is_more_diverse():
    base = unit(rng.normal(size=(1, 64)))
    tight = unit(base + 0.05 * rng.normal(size=(10, 64)))
    loose = unit(base + 1.0 * rng.normal(size=(10, 64)))
    for f in (M.extent, M.dispersion, M.pairwise_distance, M.vendi):
        assert f(loose) > f(tight)


def test_topic_measures():
    D = 1 - np.eye(4)
    one = M.topic_measures(np.zeros(8, int), D)
    assert close(one['S5'], 0) and close(one['S6'], 1) and close(one['S7'], 0)
    uni = M.topic_measures(np.arange(8) % 4, D)
    assert close(uni['S5'], math.log(4)) and close(uni['S6'], 4)
    assert close(uni['S7'], 1 - 4 * (1 / 4) ** 2)  # with d = 1 - I, Rao-Stirling is the Gini-Simpson index


def test_centroid_distances():
    D = M.centroid_distances(np.eye(3))
    assert close(D[0, 1], 1) and close(D[0, 0], 0)


def test_loo_centroid_distance():
    U = unit(np.tile(rng.normal(size=(1, 8)), (4, 1)))
    assert np.allclose(M.loo_centroid_distance(U), 0, atol=1e-7)
    assert np.isnan(M.loo_centroid_distance(U[:2])).all()
    V = np.eye(5)
    d = M.loo_centroid_distance(V)
    assert np.allclose(d, d[0]) and d[0] > 0


def test_within_paper_spread():
    P = unit(np.tile(rng.normal(size=(1, 8)), (6, 1)))
    assert close(M.within_paper_spread(P), 0, 1e-6)
    assert close(M.within_paper_spread(np.eye(6)), 1.0)
    assert math.isnan(M.within_paper_spread(np.eye(3)))
    Q = unit(rng.normal(size=(7, 10)))
    assert close(M.within_paper_spread(Q), M.pairwise_distance(Q))


def test_nearest_distance_skips_own_preprint():
    B = np.eye(4)
    u = unit(np.array([[1.0, 0.0, 0.0, 0.0]]))[0]
    assert close(M.nearest_distance(u, B), 1.0)  # the exact copy (cosine 1) is skipped; the rest are orthogonal
    v = unit(np.array([[1.0, 0.3, 0, 0]]))[0]
    assert close(M.nearest_distance(v, B, exclude_above=1.1), 1 - v[0])


def test_set_novelty():
    a = np.array([1, 2, 3], np.uint32)
    assert close(M.set_novelty(a, [np.array([1, 2, 3, 4], np.uint32)]), 0)
    assert close(M.set_novelty(a, [np.array([7, 8], np.uint32)]), 1)
    assert close(M.set_novelty(a, [np.array([1], np.uint32), np.array([2], np.uint32)]), 1 / 3)
    assert math.isnan(M.reference_novelty(a, [a], 3, rng))


# ---------------- lexical

def naive_mattr(ids, w):
    return np.mean([len(set(ids[s:s + w])) / w for s in range(len(ids) - w + 1)])


def test_mattr():
    assert close(M.mattr(np.zeros(1500, int), 1000), 1 / 1000)
    assert close(M.mattr(np.arange(1500), 1000), 1.0)
    assert math.isnan(M.mattr(np.arange(10), 1000))
    for _ in range(5):
        ids = rng.integers(0, 40, size=300)
        assert close(M.mattr(ids, 50), naive_mattr(list(ids), 50), 1e-12)


def test_unigram_entropy():
    assert close(M.unigram_entropy(np.zeros(2000, int)), 0)
    assert close(M.unigram_entropy(np.arange(2000)), math.log(1000))
    assert math.isnan(M.unigram_entropy(np.arange(999)))


def test_tokens_and_ids():
    t = M.tokens("Large-language models aren't 42 magic; models.")
    assert t == ['large-language', 'models', "aren't", 'magic', 'models']
    ids = M.token_ids(t)
    assert ids[1] == ids[4] and len(set(ids)) == 4


def test_sentences_and_readability():
    text = ' '.join(['The cat sat on the mat.'] * 10)
    s = M.sentences(text)
    assert len(s) == 10
    m, sd = M.sentence_stats(s)
    assert close(m, 6) and close(sd, 0)
    assert M.syllables('banana') == 3 and M.syllables('make') == 1 and M.syllables('table') == 2
    easy = M.flesch(s)
    hard = M.flesch(M.sentences(' '.join(['Heterogeneous computational infrastructures necessitate sophisticated orchestration methodologies.'] * 10)))
    assert easy > 90 and hard < 0


def test_marker_rate():
    assert close(M.marker_rate(['delve', 'into', 'this'], {'delve'}), 1000 / 3)


def test_trigram_set():
    t = 'the quick brown fox jumps over the lazy dog'.split()
    s = M.trigram_set(t)
    assert len(s) == 7 and s.dtype == np.uint32 and np.all(np.diff(s.astype(np.int64)) > 0)
    assert close(M.set_novelty(s, [M.trigram_set(t)]), 0)
    assert M.set_novelty(s, [M.trigram_set('a completely different sentence about cats and dogs'.split())]) == 1.0


def test_compression_ratio():
    rnd = random.Random(3)
    texts = [''.join(rnd.choice(string.ascii_lowercase + ' ') for _ in range(3000)).encode() for _ in range(5)]
    assert M.compression_ratio([texts[0]] * 5) < 0.3     # identical texts: the concatenation is one text
    assert M.compression_ratio(texts) > 0.95             # independent texts share nothing
    assert len(M.excerpt('word ' * 2000, 4000)) <= 4000


# ---------------- citations

def test_citation_measures():
    J = M.jaccard_matrix([['a', 'b'], ['a', 'b'], ['c']])
    assert close(J[0, 1], 1) and close(J[0, 2], 0) and close(M.mean_offdiag(J[:2, :2]), 1)
    assert close(M.venue_entropy(['v'] * 50, 40, rng), 0)
    assert close(M.venue_entropy(['v%d' % (i % 4) for i in range(400)], 400, rng), math.log(4))
    assert math.isnan(M.venue_entropy(['v'] * 10, 40, rng))
    assert close(M.age_spread([5] * 20), 0)
    assert close(M.self_share(['x', 'y', 'z', 'w'], {'x', 'y'}), 0.5)


# ---------------- resampling

def test_equal_size_n():
    assert M.equal_size_n([10, 40]) == 10
    assert M.equal_size_n([4, 40]) is None
    assert M.equal_size_n([10, 40], n=5) == 5
    assert M.equal_size_n([10, 40], n=12) is None


def test_resample_equal_size_removes_size_effect():
    """A 2-D Gaussian cloud, groups of 10 and 400: the raw extent of the bigger group is far larger (a size
    artifact); its equal-size estimate matches the expected extent of 10 papers."""
    r = np.random.default_rng(5)
    X = r.normal(size=(410, 2))
    groups = [X[:10], X[10:]]
    expected10 = np.mean([M.extent(r.normal(size=(10, 2))) for _ in range(4000)])
    assert M.extent(groups[1]) > expected10 + 0.8
    n, out = M.resample(lambda g, idx: dict(S1=M.extent(groups[g][idx])), [10, 400], draws=1000, rng=r)
    assert n == 10
    assert abs(out[1]['S1'] - expected10) < 0.1


def test_resample_draw_shapes():
    d = M.draws_for(10, 10, 1000, rng)
    assert d.shape == (1, 10)                    # the smaller group is used whole, once
    d = M.draws_for(20, 5, 50, rng)
    assert d.shape == (50, 5) and all(len(set(r)) == 5 for r in d)
    assert M.resample(lambda g, i: {}, [3, 30]) == (None, None)


if __name__ == '__main__':
    fails = 0
    for name, f in sorted((k, v) for k, v in globals().items() if k.startswith('test_') and callable(v)):
        try:
            f(); print('ok  ', name)
        except Exception as e:  # noqa: BLE001
            fails += 1; print('FAIL', name, type(e).__name__, e)
    print(f'{fails} failed')
    sys.exit(1 if fails else 0)
