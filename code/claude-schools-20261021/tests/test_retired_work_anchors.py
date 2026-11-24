"""Wrong source identifiers leave active resolution without changing issued IDs or losing their audit history."""
import collections
import copy
import gzip
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import atlas_ids as A
from test_atlas_ids import paper, pi, write

BAD = 'w|openalex:W2963320196'
DOI = '10.4230/lipics.approx-random.2018.34'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup(tmp_path):
    reg = tmp_path / 'registry.sqlite'; db = A.open_registry(reg, seed=False)
    anchors = [(A.RANK['doi'], 'w|doi:' + DOI), (A.RANK['oaw'], BAD),
               (A.RANK['oaw'], 'w|openalex:W2964241527')]
    issued = A.assign(db, 'work', 'atl:w:', {'legacy': sorted(anchors)}, '2026-11-05', collections.Counter())['legacy']
    other = A.assign(db, 'work', 'atl:w:', {'other': [(0, 'w|doi:10.1000/unrelated')]}, '2026-11-05', collections.Counter())['other']
    db.execute('create table source_notes (key text primary key, value text)')
    db.execute('insert into source_notes values (?,?)', ('original', 'whole backup retains all tables'))
    db.commit(); anchor = dict(zip(A._ANCHOR_COLUMNS, db.execute('select * from anchors where anchor=?', (BAD,)).fetchone()))
    entity = dict(zip(A._ID_COLUMNS, db.execute('select * from ids where id=?', (issued,)).fetchone()))
    expected = A.registry_fingerprint(db); db.close()
    review = dict(version=1, action='retire_work_anchors', id='exact-mixed-source-review', reviewed_by='fixture-reviewer',
                  reviewed_at='2026-11-08', reason='Exact source record mixes identifiers from different research papers.',
                  source_registry_sha256=sha(reg), expected_registry=expected,
                  retirements=[dict(expected_anchor=anchor, expected_id=entity)],
                  evidence=[dict(url='https://example.org/original-source.pdf', sha256='a' * 64,
                                 quote='Complete source evidence identifies the incompatible works separately.')])
    return reg, review, issued, other


def test_actual_mixed_key_leaves_active_lookup_but_issued_ids_and_whole_backup_survive(tmp_path):
    reg, review, issued, other = setup(tmp_path); before = sha(reg); backup = tmp_path / 'whole-before.sqlite'
    dry = A.retire_work_anchors(reg, review)
    assert dry['status'] == 'planned' and sha(reg) == before and not backup.exists()
    result = A.retire_work_anchors(reg, review, backup, write=True)
    assert result['status'] == 'retired' and result['issued_ID_changes'] == 0
    db = A.open_registry(reg, seed=False); old = sqlite3.connect(backup)
    assert db.execute('select * from ids order by id').fetchall() == old.execute('select * from ids order by id').fetchall()
    assert A.registry_fingerprint(old) == review['expected_registry']
    assert old.execute('select value from source_notes where key=?', ('original',)).fetchone() == ('whole backup retains all tables',)
    assert A.resolve(db, issued) == issued and A.resolve(db, other) == other
    assert not db.execute('select id from anchors where anchor=?', (BAD,)).fetchone()
    assert db.execute('select id from anchors where anchor=?', ('w|doi:' + DOI,)).fetchone() == (issued,)
    row = db.execute('select id,kind,first_seen,review_id,review_json from retired_work_anchors where anchor=?', (BAD,)).fetchone()
    assert row[:4] == (issued, 'work', '2026-11-05', review['id']) and json.loads(row[4]) == review
    assert result['backup_sha256'] == sha(backup); old.close(); db.close()
    after = sha(reg)
    assert A.retire_work_anchors(reg, review, backup, write=True)['status'] == 'already_retired'
    assert sha(reg) == after


@pytest.mark.parametrize('field', ['anchor', 'issued_id', 'whole_registry', 'physical_registry', 'evidence'])
def test_wrong_preimage_or_missing_original_proof_fails_without_mutating_registry(tmp_path, field):
    reg, review, _, other = setup(tmp_path); broken = copy.deepcopy(review)
    if field == 'anchor': broken['retirements'][0]['expected_anchor']['first_seen'] = '2026-01-01'
    if field == 'issued_id': broken['retirements'][0]['expected_id']['issued'] = '2026-01-01'
    if field == 'evidence': broken['evidence'][0].pop('quote')
    if field == 'physical_registry': broken['source_registry_sha256'] = '0' * 64
    if field == 'whole_registry':
        db = A.open_registry(reg, seed=False); db.execute('update ids set note=? where id=?', ('unreviewed unrelated edit', other)); db.commit(); db.close()
        broken['source_registry_sha256'] = sha(reg)  # Correct physical hash cannot waive the full logical preimage.
    before = sha(reg); backup = tmp_path / 'must-not-be-created.sqlite'
    with pytest.raises(ValueError): A.retire_work_anchors(reg, broken, backup, write=True)
    assert sha(reg) == before and not backup.exists()


def test_second_invalid_target_does_not_partially_retire_first_and_existing_backup_is_never_overwritten(tmp_path):
    reg, review, _, _ = setup(tmp_path); broken = copy.deepcopy(review); extra = copy.deepcopy(broken['retirements'][0])
    extra['expected_anchor']['anchor'] = 'w|openalex:W999999'; broken['retirements'].append(extra)
    before = sha(reg)
    with pytest.raises(ValueError, match='anchor preimage'): A.retire_work_anchors(reg, broken, tmp_path / 'backup', write=True)
    assert sha(reg) == before
    backup = tmp_path / 'backup'; backup.write_bytes(b'owner receipt')
    with pytest.raises(ValueError, match='new file'): A.retire_work_anchors(reg, review, backup, write=True)
    assert backup.read_bytes() == b'owner receipt' and sha(reg) == before


def test_quarantine_cannot_be_automatically_reused_and_failed_run_preserves_all_science_and_ids(tmp_path):
    reg, review, issued, _ = setup(tmp_path); A.retire_work_anchors(reg, review, tmp_path / 'backup', write=True)
    root = tmp_path / 'package'; fx = {'example': dict(pis=[pi('Madhu Sudan')], students={}, links=[], sweep=[],
            papers=[paper('Madhu Sudan', 'https://openalex.org/W2963320196', doi=DOI, title='Mixed source')])}
    write(root, fx); files = {p.name: p.read_bytes() for p in (root / 'example').iterdir()}; db = A.open_registry(reg, seed=False)
    before = A.registry_fingerprint(db)
    with pytest.raises(A.WorkIDConflict, match='retired work anchor') as exc:
        A.run(['example'], root, db, use_sweep=False)
    assert exc.value.holds[0]['retirement_reviews'] == {BAD: review['id']}
    assert A.registry_fingerprint(db) == before and A.resolve(db, issued) == issued
    assert {p.name: p.read_bytes() for p in (root / 'example').iterdir()} == files
    with pytest.raises(sqlite3.IntegrityError, match='cannot become active'):
        db.execute('insert into anchors values (?,?,?,?)', (BAD, issued, 'work', '2026-11-08'))
    db.rollback()
    with pytest.raises(sqlite3.IntegrityError, match='immutable'): db.execute('delete from retired_work_anchors')
    db.rollback(); db.close()


def test_good_polar_anchor_and_unrelated_work_keep_ids_and_active_export_excludes_only_retired_key(tmp_path):
    reg, review, issued, other = setup(tmp_path); A.retire_work_anchors(reg, review, tmp_path / 'backup', write=True)
    root = tmp_path / 'package'; fx = {'example': dict(pis=[pi('Madhu Sudan')], students={}, links=[], sweep=[], papers=[
        paper('Madhu Sudan', 'https://openalex.org/W2964241527', doi=DOI, title='Polar Codes'),
        paper('Madhu Sudan', 'https://openalex.org/W999', doi='10.1000/unrelated', title='Unrelated research')])}
    write(root, fx); db = A.open_registry(reg, seed=False); result = A.run(['example'], root, db, use_sweep=False)
    rows = [json.loads(line) for line in gzip.open(root / 'example/lab_papers.jsonl.gz', 'rt')]
    assert [r['atlasWorkId'] for r in rows] == [issued, other]
    text = gzip.open(root / 'ids/crossref.tsv.gz', 'rt').read()
    assert 'W2963320196' not in text and 'W2964241527' in text and DOI in text
    assert result['report']['registry']['retired_work_anchors'] == 1
    assert db.execute('select count(*) from retired_work_anchors').fetchone() == (1,); db.close()


def test_retired_edition_cannot_hide_behind_a_source_distinct_work_split(tmp_path):
    reg, review, _, _ = setup(tmp_path); A.retire_work_anchors(reg, review, tmp_path / 'backup', write=True)
    # This shared edition joins two rows of the same PI; normal splitting would discard their edition anchors.
    edition = dict(oa='https://openalex.org/W2963320196')
    fx = {'example': dict(pis=[pi('Madhu Sudan')], students={}, links=[], sweep=[], papers=[
        paper('Madhu Sudan', 'https://openalex.org/W2964241527', doi=DOI, editions=[edition], title='Polar Codes'),
        paper('Madhu Sudan', 'https://openalex.org/W999', doi='10.1000/unrelated', editions=[edition], title='Other paper')])}
    root = tmp_path / 'package'; write(root, fx); files = {p.name: p.read_bytes() for p in (root / 'example').iterdir()}
    db = A.open_registry(reg, seed=False); before = A.registry_fingerprint(db)
    with pytest.raises(A.WorkIDConflict, match='retired work anchor'):
        A.run(['example'], root, db, use_sweep=False)
    assert A.registry_fingerprint(db) == before
    assert {p.name: p.read_bytes() for p in (root / 'example').iterdir()} == files; db.close()


def test_isolated_cli_dry_run_and_apply_use_exact_review_without_importing_caller_modules(tmp_path):
    reg, review, _, _ = setup(tmp_path); reviewed = tmp_path / 'review.json'; reviewed.write_text(json.dumps(review))
    marker = tmp_path / 'caller-imported'; (tmp_path / 'atlas_paths.py').write_text('raise RuntimeError("caller module imported")')
    script = Path(A.__file__); env = dict(os.environ, CS_ATLAS_TOOLS=str(script.parent))
    cmd = [sys.executable, '-I', str(script), '--registry', str(reg), '--retire-work-anchors', str(reviewed)]
    before = sha(reg); result = subprocess.run(cmd, cwd=tmp_path, env=env, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)['status'] == 'planned' and sha(reg) == before and not marker.exists()
    result = subprocess.run(cmd + ['--apply-retirements', '--retirement-backup', str(tmp_path / 'whole-backup.sqlite')],
                            cwd=tmp_path, env=env, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)['status'] == 'retired'
