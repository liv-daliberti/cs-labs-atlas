"""Materialize reviewed Harvard paper evidence through the existing generic DBLP recovery format.

Offline; validates immutable source bytes. Run before a Harvard build:
  bin/atlas run hierarchy/harvard/materialize_recoveries.py
The reviewed JSON and initial/fixed accuracy panels preserve why each source was admitted.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import atlas_paths as P  # noqa: E402


def main():
    reviewed = json.loads((Path(__file__).parent / 'reviewed/paper-recovery-review.json').read_text())
    out = P.data_w('dblp-recovered.jsonl.gz', 'harvard')
    rows = [json.loads(line) for line in gzip.open(out, 'rt')] if out.exists() else []
    by_key = {(row['pi'], row['dblp_key']): row for row in rows}
    for row in reviewed:
        for source in row['review_sources']:
            raw = (P.CODE / source['artifact']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ValueError('reviewed source hash mismatch: ' + source['artifact'])
        by_key[(row['pi'], row['dblp_key'])] = {k: v for k, v in row.items() if k != 'review_sources'}
    with P.gzip_text(out) as fh:
        for key in sorted(by_key):
            fh.write(json.dumps(by_key[key], ensure_ascii=False) + '\n')
    print(json.dumps(dict(reviewed=len(reviewed), materialized=len(by_key), out=str(out))))


if __name__ == '__main__':
    main()
