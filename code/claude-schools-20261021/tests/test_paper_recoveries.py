"""Reviewed recoveries must not overwrite unrelated data or admit altered sources."""
import gzip
import hashlib
import json

import pytest

from paper_recoveries import materialize


def test_verified_recovery_preserves_existing_rows_and_is_idempotent(tmp_path):
    source = tmp_path / 'paper.pdf'
    source.write_bytes(b'verified source bytes')
    review = tmp_path / 'review.json'
    row = {'pi': 'New PI', 'dblp_key': 'journals/example/1', 'title': 'Reviewed paper'}
    review.write_text(json.dumps([{**row, 'review_sources': [
        {'artifact': 'paper.pdf', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]}]))
    out = tmp_path / 'recoveries.jsonl.gz'
    old = {'pi': 'Existing PI', 'dblp_key': 'conf/example/2', 'title': 'Preserved paper'}
    with gzip.open(out, 'wt') as f:
        f.write(json.dumps(old) + '\n')
    materialize(review, tmp_path, out)
    first = out.read_bytes()
    materialize(review, tmp_path, out)
    assert out.read_bytes() == first
    with gzip.open(out, 'rt') as f:
        assert [json.loads(line) for line in f] == [old, row]
    source.write_bytes(b'changed after review')
    with pytest.raises(ValueError, match='source hash mismatch'):
        materialize(review, tmp_path, out)
    assert out.read_bytes() == first
