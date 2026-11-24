"""The all-AI rewrite study (ai-writing/allai): the preservation checks, the rewrite acceptance rule and the geometry helpers on fixtures
(numpy only; no model, no GPU)."""
import numpy as np

import allai_math as A
import preserve as PR
import rewrite as RW


def test_numbers_and_terms_kept():
    src = 'BERT reaches 92.5% accuracy on GLUE with 1,000 steps and ResNet-50 uses 3 layers.'
    f = PR.checks(src, 'Using 1000 steps, BERT attains 92.5 percent on GLUE; ResNet50 has 3 layers.')
    assert (f['num_lost'], f['num_new'], f['term_lost']) == (0, 0, 0)
    assert f['n_num'] == 3 and f['n_term'] == 3
    assert PR.keep_rule(1, '', f) == (True, '')


def test_numbers_lost_and_added_and_terms_lost():
    src = 'We obtain 12 and 34 and 56 and 78 points; GPT-4 and LoRA are used.'
    lost = PR.checks(src, 'We obtain 12 points; GPT-4 and LoRA are used.')
    assert lost['num_lost'] == 3 and PR.keep_rule(1, '', lost) == (False, 'numbers_lost')
    added = PR.checks('We get 5 points.', 'We get 5 points, up 17 and 18 and 19.')
    assert added['num_new'] == 3 and PR.keep_rule(1, '', added) == (False, 'numbers_added')
    gone = PR.checks('LoRA and BERT help.', 'Adapters help.')
    assert gone['term_lost'] == 2 and PR.keep_rule(1, '', gone) == (False, 'terms_lost')
    assert PR.keep_rule(0, 'truncated', {}) == (False, 'truncated')


def test_decimal_point_is_not_a_number_boundary():
    assert PR.numbers('values of 0.5 and 3.14, then 2020.') == ['0.5', '3.14', '2020']


def test_accept_rule():
    assert RW.accept('word ' * 100, 100, 'stop', True) == (1, '')
    assert RW.accept('word ' * 100, 100, 'length', True) == (0, 'truncated')
    assert RW.accept('word ' * 100, 100, 'stop', False) == (0, 'refusal_or_short')
    assert RW.accept('word ' * 10, 100, 'stop', True) == (0, 'much_shorter_than_source')
    assert RW.accept('word ' * 9, 12, 'stop', True) == (1, '')


def test_prompt_names_title_and_length():
    p = RW.build_prompt('A Title', 'one two three', 'polish')
    assert '"A Title"' in p and 'about 3 words' in p and p.endswith('one two three')
    assert 'Paraphrase' in RW.build_prompt('T', 'a b', 'paraphrase')


def test_shards_are_disjoint_and_complete():
    ids = [f'atl:w:{i}' for i in range(500)]
    got = [[i for i in ids if RW.shard_of(i, 3) == s] for s in range(3)]
    assert sum(map(len, got)) == 500 and len(set(sum(got, []))) == 500


def test_gram_geometry_identical_and_orthogonal():
    U = np.tile(np.array([[1.0, 0, 0, 0]]), (5, 1))
    d, p, v = A.gram_geometry(U)
    assert d == 0 and abs(p) < 1e-9 and abs(v - 1) < 1e-6
    d, p, v = A.gram_geometry(np.eye(4))
    assert abs(v - 4) < 1e-6 and abs(p - 1) < 1e-9 and d > 0


def test_nearest_centroid_and_entropy():
    cent = np.eye(3)
    Z = np.array([[1.0, 0.1, 0], [0, 1, 0.2], [0, 0.1, 1], [0.9, 0, 0]])
    lab = A.nearest_centroid(Z, cent, chunk=2)
    assert lab.tolist() == [0, 1, 2, 0]
    assert abs(A.entropy_bits(np.array([0, 1]), 3) - 1.0) < 1e-9 and A.entropy_bits(np.array([2, 2, 2]), 3) == 0.0
