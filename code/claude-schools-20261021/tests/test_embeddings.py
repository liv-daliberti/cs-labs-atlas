"""The all-papers embeddings study (ai-writing/embeddings): the store, its index and resume, the chunking and batching helpers, the OpenAlex
abstract rebuild and the novelty maths, on small fixtures (numpy and sqlite only; no model, no GPU)."""
import json
import sqlite3
import zlib

import numpy as np
import pytest

import embed
import novelty
import oa_fields
import store
import texts

D = 8


def vec(seed, n=1):
    return np.random.default_rng(seed).normal(size=(n, D)).astype(np.float16)


def put_part(emb, model, kind, name, ids, seeds, ns=None, sparse=False):
    ns = ns or [1] * len(ids)
    X = np.vstack([vec(s, n) for s, n in zip(seeds, ns)])
    M = np.vstack([X[sum(ns[:i]):sum(ns[:i + 1])].astype(np.float32).mean(0) for i in range(len(ids))]).astype(np.float16) if kind == 'fulltext' else None
    sp = None
    if sparse:
        sp = (np.arange(len(ids) + 1) * 2, np.tile(np.array([3, 9], np.int32), len(ids)), np.tile(np.array([0.5, 0.25], np.float16), len(ids)))
    store.write_part(store.part_dir(model, kind, emb) / f'part_{name}.npz', ids, [f'h{s}' for s in seeds], ns, X, M, [10 * n for n in ns], sp)
    return X


# ---------------------------------------------------------------- store
def test_part_merge_and_container_layout(tmp_path):
    put_part(tmp_path, 'm', 'abstract', 'a_0', ['p1', 'p2', 'p3'], [1, 2, 3])
    out = store.merge('m', 'abstract', {'p1': 'cmu', 'p2': 'mit', 'p3': 'cmu'}, dict(hf='x/y', revision='abc'), emb=tmp_path)
    assert out == {'cmu': 2, 'mit': 1}
    assert not store.part_files('m', 'abstract', tmp_path)                       # merged parts are removed
    c = store.load('m', 'cmu', 'abstract', emb=tmp_path)
    assert list(c['ids']) == ['p1', 'p3'] and c['M'].shape == (2, D) and c['M'].dtype == np.float16
    assert np.array_equal(c['M'][1], vec(3)[0])
    db = sqlite3.connect(tmp_path / 'm' / 'cmu' / 'abstract.index.sqlite')
    assert db.execute('select paper_id, row, n, text_hash from papers order by row').fetchall() == [('p1', 0, 1, 'h1'), ('p3', 1, 1, 'h3')]
    m = store.meta('m', 'cmu', 'abstract', emb=tmp_path)
    assert m['hf'] == 'x/y' and m['revision'] == 'abc' and m['school'] == 'cmu' and m['dim'] == D and m['papers'] == 2


def test_fulltext_keeps_chunks_and_mean(tmp_path):
    X = put_part(tmp_path, 'm', 'fulltext', 'a_0', ['p1', 'p2'], [1, 2], ns=[3, 2])
    store.merge('m', 'fulltext', {'p1': 'cmu', 'p2': 'cmu'}, {}, emb=tmp_path)
    c = store.load('m', 'cmu', 'fulltext', chunks=True, emb=tmp_path)
    assert c['X'].shape == (5, D) and list(c['n']) == [3, 2] and list(c['off']) == [0, 3, 5]
    assert np.array_equal(c['X'], X)
    assert np.allclose(c['M'][0].astype(np.float32), X[:3].astype(np.float32).mean(0), atol=1e-2)


def test_resume_sees_parts_and_containers_and_hashes(tmp_path):
    put_part(tmp_path, 'm', 'abstract', 'a_0', ['p1', 'p2'], [1, 2])
    assert store.done_map('m', 'abstract', tmp_path) == {'p1': 'h1', 'p2': 'h2'}        # unmerged parts count
    store.merge('m', 'abstract', {'p1': 'cmu', 'p2': 'mit'}, {}, emb=tmp_path)
    put_part(tmp_path, 'm', 'abstract', 'b_0', ['p3'], [3])
    assert store.done_map('m', 'abstract', tmp_path) == {'p1': 'h1', 'p2': 'h2', 'p3': 'h3'}  # containers and parts together
    # a changed text (new hash) is not done: the todo compares hashes
    assert store.done_map('m', 'abstract', tmp_path)['p1'] != 'h9'


def test_merge_new_part_wins_and_keeps_old_rows(tmp_path):
    put_part(tmp_path, 'm', 'abstract', 'a_0', ['p1', 'p2'], [1, 2])
    store.merge('m', 'abstract', {'p1': 'cmu', 'p2': 'cmu'}, {}, emb=tmp_path)
    put_part(tmp_path, 'm', 'abstract', 'b_0', ['p2', 'p3'], [22, 3])                   # p2 re-embedded from a changed text
    store.merge('m', 'abstract', {'p1': 'cmu', 'p2': 'cmu', 'p3': 'cmu'}, {}, emb=tmp_path)
    c = store.load('m', 'cmu', 'abstract', emb=tmp_path)
    assert list(c['ids']) == ['p1', 'p2', 'p3']
    assert np.array_equal(c['M'][0], vec(1)[0]) and np.array_equal(c['M'][1], vec(22)[0]) and list(c['hashes']) == ['h1', 'h22', 'h3']


def test_merge_drops_papers_without_a_home_school_and_survives_a_killed_part(tmp_path):
    put_part(tmp_path, 'm', 'abstract', 'a_0', ['p1', 'ghost'], [1, 2])
    (store.part_dir('m', 'abstract', tmp_path) / 'tmp_1_x.npz').write_bytes(b'partial')  # a killed job's temp file is never read
    assert store.merge('m', 'abstract', {'p1': 'cmu'}, {}, emb=tmp_path) == {'cmu': 1}
    assert len(store.part_files('m', 'abstract', tmp_path)) == 0


def test_sparse_lexical_weights_round_trip(tmp_path):
    put_part(tmp_path, 'm', 'abstract', 'a_0', ['p1', 'p2'], [1, 2], sparse=True)
    store.merge('m', 'abstract', {'p1': 'cmu', 'p2': 'cmu'}, {}, emb=tmp_path)
    c = store.load('m', 'cmu', 'abstract', emb=tmp_path)
    assert list(c['sp_ptr']) == [0, 2, 4] and list(c['sp_idx'][:2]) == [3, 9] and float(c['sp_val'][1]) == 0.25


# ---------------------------------------------------------------- embed helpers
def test_windows_tail_cap_and_empty():
    w = embed.windows(list(range(10)), 4, 8, 3)
    assert [len(x) for x in w] == [4, 4]                       # the 2-token tail is dropped
    assert [len(x) for x in embed.windows(list(range(2)), 4, 8, 3)] == [2]   # ... unless it is the only window
    big = embed.windows(list(range(400)), 4, 8, 1)             # 100 windows, cap 8: evenly spaced, first and last kept
    assert len(big) == 8 and big[0][0] == 0 and big[-1][0] == 396
    assert embed.windows([], 4, 8, 1) == []


def test_make_batches_respects_budget_and_covers_everything():
    lengths = np.array([5, 100, 7, 100, 3, 50])
    bs = embed.make_batches(lengths, 120)
    assert sorted(i for b in bs for i in b) == list(range(6))
    for b in bs:
        assert len(b) * lengths[b].max() <= 120 or len(b) == 1
    assert [lengths[b].max() for b in bs] == sorted(lengths[b].max() for b in bs)   # sorted by length


def test_shards_are_disjoint_and_stable():
    ids = [f'atl:w:{i:04x}' for i in range(500)]
    owner = [embed.shard_of(i, 4) for i in ids]
    assert set(owner) == {0, 1, 2, 3} and owner == [embed.shard_of(i, 4) for i in ids]
    assert all(embed.shard_of(i, 1) == 0 for i in ids)


def test_merge_sparse_takes_the_max_per_token():
    idx, val = embed.merge_sparse([{5: 0.1, 2: 0.4}, {5: 0.3}])
    assert list(idx) == [2, 5] and np.allclose(val.astype(np.float32), [0.4, 0.3], atol=1e-3)


# ---------------------------------------------------------------- OpenAlex fields and abstracts
def test_abstract_text_rebuilds_word_order():
    assert oa_fields.abstract_text({'cats': [1], 'we': [0], 'study': [2], 'we2': [3]}) == 'we cats study we2'
    assert oa_fields.abstract_text(None) is None and oa_fields.abstract_text({}) is None


def test_filter_lines_keeps_only_wanted_ids_and_projects_topics():
    w = {'id': 'https://openalex.org/W42', 'title': 'T', 'publication_year': 2020, 'type': 'article', 'language': 'en', 'updated_date': 'd',
         'abstract_inverted_index': {'hello': [0], 'world': [1]},
         'primary_topic': {'id': 'https://openalex.org/T7', 'display_name': 'Deep learning', 'score': 0.9, 'subfield': {'display_name': 'AI'},
                           'field': {'display_name': 'CS'}, 'domain': {'display_name': 'Physical Sciences'}},
         'topics': [], 'keywords': [{'display_name': 'k1'}]}
    other = dict(w, id='https://openalex.org/W43')
    n, rows = oa_fields.filter_lines([json.dumps(w).encode(), json.dumps(other).encode(), b''], {'W42'}, '2026-10-14')
    assert n == 3 and len(rows) == 1 and rows[0][0] == 'W42' and rows[0][6] == 'hello world'
    assert json.loads(rows[0][7]) == dict(id='T7', name='Deep learning', score=0.9, subfield='AI', field='CS', domain='Physical Sciences')
    assert json.loads(rows[0][9]) == ['k1'] and rows[0][10] == '2026-10-14'


def test_abstract_rows_prefers_snapshot_then_api_cache_and_drops_scraps(tmp_path):
    db = sqlite3.connect(tmp_path / 'oa.sqlite')
    db.execute(oa_fields.SCHEMA.split(';')[0])
    ab = ' '.join(['word'] * 30)
    db.execute("insert into works (id, abstract) values ('W1', ?)", (ab,)); db.execute("insert into works (id, abstract) values ('W2', 'Abstract')")
    db.commit(); db.close()
    api = sqlite3.connect(tmp_path / 'api.sqlite')
    api.execute('create table abstracts (oa text primary key, inverted blob)')
    api.execute('insert into abstracts values (?,?)', ('https://openalex.org/W3', zlib.compress(json.dumps({w: [i] for i, w in enumerate(('a%d' % j for j in range(20)))}).encode())))
    api.commit(); api.close()
    papers = [('p1', 'https://openalex.org/W1', 'T1', 2020, 'cmu'), ('p2', 'https://openalex.org/W2', 'T2', 2020, 'cmu'),
              ('p3', 'https://openalex.org/W3', 'T3', 2021, 'mit'), ('p4', None, 'T4', 2021, 'mit')]
    rows = texts.abstract_rows(papers, tmp_path / 'oa.sqlite', tmp_path / 'api.sqlite')
    assert [(r[0], r[3]) for r in rows] == [('p1', 'oa_snapshot'), ('p3', 'api_cache')]
    assert rows[0][5] != rows[1][5] and rows[0][4] == 30


def test_usable_rule_matches_the_diversity_battery():
    assert texts.usable('pdf', 1500, {'title_found': True}) and not texts.usable('pdf', 1500, {'title_found': False})
    assert texts.usable('xml', 1500, {}) and not texts.usable('xml', 999, {})


# ---------------------------------------------------------------- novelty
def fixture(n=120, seed=0):
    rng = np.random.default_rng(seed)
    Z, _ = novelty.center_normalize(rng.normal(size=(n, D)))
    years = rng.integers(2016, 2022, size=n)
    return Z, years


@pytest.mark.parametrize('k', [1, 3, 5])
def test_novelty_matches_brute_force(k):
    Z, years = fixture()
    idx = np.arange(len(years))
    r = novelty.novelty_group(Z, years, idx, ks=(k,), nn=5, cap=0)
    ref = novelty.brute(Z, years, list(idx), k, 5)
    for p, a, b, n in zip(r['paper'], r['nov_max'], r['nov_nn'], r['n_ref']):
        ra, rb, rn = ref[p]
        assert n == rn
        if rn == 0:
            assert np.isnan(a) and np.isnan(b)
        else:
            assert a == pytest.approx(ra, abs=1e-5) and b == pytest.approx(rb, abs=1e-5)


def test_novelty_excludes_own_year_and_handles_empty_pool():
    Z = np.array([[1, 0], [1, 0], [0, 1]], np.float32)
    years = np.array([2016, 2016, 2017])
    r = novelty.novelty_group(Z, years, np.arange(3), ks=(1,), nn=1, cap=0)
    by = dict(zip(r['paper'], zip(r['nov_max'], r['n_ref'])))
    assert by[0][1] == 0 and np.isnan(by[0][0]) and by[1][1] == 0   # the two 2016 papers do not see each other
    assert by[2][0] == pytest.approx(1.0) and by[2][1] == 2         # 2017 paper is orthogonal to both 2016 papers


def test_novelty_window_grows_with_k_and_never_lowers_max_novelty():
    Z, years = fixture(200, 1)
    r = novelty.novelty_group(Z, years, np.arange(200), ks=(1, 3, 5), nn=5, cap=0)
    by = {(p, k): (a, n) for p, k, a, n in zip(r['paper'], r['k'], r['nov_max'], r['n_ref'])}
    for p in range(200):
        if by[(p, 1)][1] and by[(p, 5)][1]:
            assert by[(p, 5)][0] <= by[(p, 1)][0] + 1e-6 and by[(p, 5)][1] >= by[(p, 1)][1]


def test_capped_pool_is_a_subset_of_the_full_pool():
    Z, years = fixture(300, 2)
    r = novelty.novelty_group(Z, years, np.arange(300), ks=(5,), nn=3, cap=20, seed=3)
    ok = r['n_ref'] > 20
    assert ok.any() and (r['n_ref_cap'][ok] == 20).all()
    assert (r['nov_max_cap'][ok] >= r['nov_max'][ok] - 1e-6).all()    # fewer references can only be farther away
    again = novelty.novelty_group(Z, years, np.arange(300), ks=(5,), nn=3, cap=20, seed=3)
    assert np.array_equal(np.nan_to_num(r['nov_max_cap']), np.nan_to_num(again['nov_max_cap']))   # fixed seed


def test_scopes_restrict_the_pool_to_the_scope():
    Z = np.array([[1, 0], [1, 0], [0, 1], [0, 1]], np.float32)
    years = np.array([2016, 2017, 2016, 2017])
    r = novelty.novelty_scopes(Z, years, [('lab', 'A', np.array([0, 1])), ('lab', 'B', np.array([0, 2, 1, 3])), ('lab', 'C', np.array([]))], ks=(1,), nn=1, cap=0)
    got = {(s, int(p)): (round(float(a), 3) if a == a else None) for s, p, a in zip(r['scope_id'], r['paper'], r['nov_max'])}
    assert got[('A', 1)] == 0.0 and got[('B', 1)] == 0.5 - 0.5 and got[('B', 3)] == 0.0
    assert ('C', 0) not in got


def test_center_normalize_gives_unit_rows():
    X = np.random.default_rng(0).normal(size=(10, D)) + 5
    Z, mu = novelty.center_normalize(X)
    assert np.allclose(np.linalg.norm(Z, axis=1), 1, atol=1e-4) and mu.shape == (D,)


# ---------------------------------------------------------------- entropy and intervals
def test_shannon_known_values_and_bias_correction():
    import measures as M
    assert M.shannon([1, 1, 1, 1]) == pytest.approx(2.0) and M.shannon([5, 0, 0]) == 0.0 and np.isnan(M.shannon([0, 0]))
    assert M.miller_madow([1, 1, 1, 1]) == pytest.approx(2.0 + 3 / (2 * 4 * np.log(2)))
    assert M.miller_madow([10, 0]) == pytest.approx(0.0)           # one occupied topic: no correction


def test_rarefied_entropy_is_deterministic_and_size_matched():
    import measures as M
    a = M.rarefied([50, 50, 50, 50], 20, reps=40, seed=1)
    assert a == M.rarefied([50, 50, 50, 50], 20, reps=40, seed=1) and 1.7 < a <= 2.0
    assert np.isnan(M.rarefied([3, 2], 10))
    assert M.rarefied([100, 0], 10) == 0.0


def test_diff_ci_covers_a_known_shift_and_resamples_clusters():
    import measures as M
    rng = np.random.default_rng(0)
    clusters = np.repeat(np.arange(60), 10)
    post = np.tile(np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1], bool), 60)
    vals = rng.normal(0, 0.1, 600) + 0.3 * post + np.repeat(rng.normal(0, 0.05, 60), 10)
    est, lo, hi, n = M.diff_ci(vals, clusters, post, reps=300)
    assert n == 60 and lo < 0.3 < hi and est == pytest.approx(0.3, abs=0.05) and hi - lo < 0.1


def test_mean_by_year_matches_plain_means():
    import measures as M
    rng = np.random.default_rng(1)
    years = np.tile([2020, 2021, 2022], 100); clusters = np.repeat(np.arange(30), 10); vals = rng.normal(size=300) + (years - 2020)
    out = M.mean_by_year(vals, years, clusters, reps=200)
    for y in (2020, 2021, 2022):
        m, lo, hi, n = out[y]
        assert m == pytest.approx(vals[years == y].mean()) and lo < m < hi and n == 100
