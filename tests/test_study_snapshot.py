"""The snapshot tooling of the 12-school study (ai-writing/study): hashing, row counts, the delta fetch's text rebuild (stdlib + pandas)."""
import gzip
import json
import sqlite3

import pytest

pytest.importorskip('pandas')
import study_delta_oa as study_delta  # noqa: E402
import study_snapshot as S  # noqa: E402


def test_sha256_and_rows(tmp_path):
    p = tmp_path / 'a.jsonl.gz'
    with gzip.open(p, 'wt') as f:
        f.write('{"a":1}\n{"a":2}\n')
    q = tmp_path / 'b.json'
    q.write_text(json.dumps([1, 2, 3]))
    db = tmp_path / 'c.sqlite'
    c = sqlite3.connect(db)
    c.execute('create table t (x int)')
    c.executemany('insert into t values (?)', [(1,), (2,)])
    c.commit(); c.close()
    assert S.rows_of(p) == 2 and S.rows_of(q) == 3 and S.rows_of(db) == {'t': 2}
    assert len(S.sha256(p)) == 64 and S.sha256(p) == S.sha256(p)


def test_place_link_copy_and_ref(tmp_path):
    src = tmp_path / 'src.bin'
    src.write_bytes(b'x' * 10)
    assert S.place(src, tmp_path / 'd' / 'l.bin', 'link') == 'link'
    assert (tmp_path / 'd' / 'l.bin').stat().st_ino == src.stat().st_ino
    assert S.place(src, tmp_path / 'd' / 'c.bin', 'copy') == 'copy'
    assert S.place(src, tmp_path / 'd' / 'r.bin', 'ref') == 'ref' and not (tmp_path / 'd' / 'r.bin').exists()


def test_inverted_index_text():
    assert study_delta.inverted_text({'b': [1], 'a': [0], 'c': [2]}) == 'a b c'
    assert study_delta.inverted_text(None) is None
