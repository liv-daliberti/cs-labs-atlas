"""Source-distinct work splits replay stably; this does not resolve or approve conflicting bibliography metadata."""
import collections
import copy
import gzip
import json

import pytest

import atlas_ids as A
from test_atlas_ids import paper, pi, write

CASES = [
    ('10.4230/lipics.approx-random.2018.34',
     ('W2964241527', 'Polar Codes with Exponentially Small Error at Finite Block Length'),
     ('W2963320196', 'Algorithmic Polarization for Hidden Markov Models')),
    ('10.4230/lipics.icalp.2025.11',
     ('W4391709362', 'A Dense Model Theorem for the Boolean Slice'),
     ('W7110215342', 'A Near-Optimal Polynomial Distance Lemma over Boolean Slices')),
]


def fx(case, another_lab=False):
    doi, *works = case; name = 'Madhu Sudan'
    rows = [paper(name, 'https://openalex.org/' + key, doi=doi, title=title) for key, title in works]
    if another_lab: rows += [dict(r, pi='Another PI') for r in rows]
    return {'example': dict(pis=[pi(name)] + ([pi('Another PI')] if another_lab else []), students={}, papers=rows, links=[], sweep=[])}


def seed(reg, case):
    doi, *works = case; db = A.open_registry(reg, seed=False)
    # Reproduce an older registry that had incorrectly treated the two source OA keys as one DOI identity.
    anchors = [(A.RANK['doi'], 'w|doi:' + doi)] + [(A.RANK['oaw'], 'w|openalex:' + k) for k, _ in works]
    issued = A.assign(db, 'work', 'atl:w:', {'old': sorted(anchors)}, '2026-11-07', collections.Counter())['old']
    db.commit(); db.close(); return issued


def run(root, reg, data, reverse=False):
    write(root, data, reverse=reverse); db = A.open_registry(reg, seed=False)
    try:
        result = A.run(['example'], root, db, today='2026-11-08', use_sweep=False)
        state = {'ids': db.execute('select * from ids order by id').fetchall(), 'anchors': db.execute('select * from anchors order by anchor').fetchall()}
    finally: db.close()
    rows = [json.loads(x) for x in gzip.open(root / 'example/lab_papers.jsonl.gz', 'rt')]
    return result, state, rows


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('another_lab', [False, True])
def test_two_actual_collision_shapes_keep_source_rows_and_replay_without_minting(case, another_lab, tmp_path):
    reg = tmp_path / 'registry.sqlite'; issued = seed(reg, case); data = fx(case, another_lab)
    first, state, rows = run(tmp_path / 'first', reg, data)
    assert first['report']['stats']['work_components_split'] == 1
    assert first['report']['stats']['split_minted'] == 1
    assert first['report']['stats']['split_work_anchors_rebound'] == 1
    assert len(set(first['work_of'].values())) == 2
    assert issued in first['work_of'].values()
    for row, raw in zip(rows, data['example']['papers']):
        assert {k: v for k, v in row.items() if k != 'atlasWorkId'} == raw
    again, state2, again_rows = run(tmp_path / 'again', reg, data)
    assert state2 == state and first['work_of'] == again['work_of']
    assert again_rows == rows
    assert again['report']['stats'].get('minted', 0) == again['report']['stats'].get('split_minted', 0) == 0
    assert again['report']['stats'].get('redirects_new', 0) == 0
    db = A.open_registry(reg, seed=False)
    # The shared DOI remains ambiguous; ID stability never certifies its attribution or changes source metadata.
    assert db.execute('select id from anchors where anchor=?', ('w|doi:' + case[0],)).fetchone()[0] == issued
    assert db.execute("select count(*)from ids where status='redirect'").fetchone()[0] == 0; db.close()


@pytest.mark.parametrize('case', CASES)
def test_source_key_IDs_are_stable_under_reordered_rows(case, tmp_path):
    reg = tmp_path / 'registry.sqlite'; seed(reg, case); data = fx(case)
    _, _, first = run(tmp_path / 'first', reg, data)
    _, _, second = run(tmp_path / 'second', reg, data, reverse=True)
    assert {r['oa']: r['atlasWorkId'] for r in first} == {r['oa']: r['atlasWorkId'] for r in second}


def test_no_source_unique_anchor_holds_and_rolls_back_all_unpublished_assignments(tmp_path):
    data = fx(CASES[0]); rows = data['example']['papers']; rows[1]['oa'] = rows[0]['oa']
    root = tmp_path / 'trial'; write(root, data); originals = {p.name: p.read_bytes() for p in (root / 'example').iterdir()}
    db = A.open_registry(tmp_path / 'registry.sqlite', seed=False)
    with pytest.raises(A.WorkIDConflict, match='unambiguous') as exc:
        A.run(['example'], root, db, use_sweep=False)
    assert exc.value.holds
    assert db.execute('select count(*)from ids').fetchone()[0] == db.execute('select count(*)from anchors').fetchone()[0] == 0
    assert {p.name: p.read_bytes() for p in (root / 'example').iterdir()} == originals
    db.close()


def test_unrelated_issued_work_IDs_and_original_metadata_remain_unchanged(tmp_path):
    reg = tmp_path / 'registry.sqlite'; data = fx(CASES[0]); other = paper('Madhu Sudan', 'https://openalex.org/W999', doi='10.1000/unrelated', title='Unrelated work')
    initial = copy.deepcopy(data); initial['example']['papers'] = [other]
    _, before_state, before_rows = run(tmp_path / 'before', reg, initial)
    seed(reg, CASES[0]); data['example']['papers'].append(other)
    _, after_state, after_rows = run(tmp_path / 'after', reg, data)
    old = before_rows[0]['atlasWorkId']; assert after_rows[-1]['atlasWorkId'] == old
    assert next(r for r in before_state['ids'] if r[0] == old) == next(r for r in after_state['ids'] if r[0] == old)
