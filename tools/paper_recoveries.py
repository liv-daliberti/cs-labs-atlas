"""Materialize reviewed paper evidence through the existing DBLP recovery format.

Offline; validates immutable source bytes. Run before a Harvard build:
  bin/atlas run tools/paper_recoveries.py harvard
The reviewed JSON and initial/fixed accuracy panels preserve why each source was admitted.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import atlas_paths as P
import school_config as S


def materialize(reviewed_path, source_root, out):
    reviewed = json.loads(Path(reviewed_path).read_text())
    rows = [json.loads(line) for line in gzip.open(out, 'rt')] if out.exists() else []
    by_key = {(row['pi'], row['dblp_key']): row for row in rows}
    for row in reviewed:
        for source in row['review_sources']:
            raw = (Path(source_root) / source['artifact']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ValueError('reviewed source hash mismatch: ' + source['artifact'])
        by_key[(row['pi'], row['dblp_key'])] = {k: v for k, v in row.items() if k != 'review_sources'}
    temporary = out.with_name(out.name + '.tmp')
    with P.gzip_text(temporary) as fh:
        for key in sorted(by_key):
            fh.write(json.dumps(by_key[key], ensure_ascii=False) + '\n')
    temporary.replace(out)
    return dict(reviewed=len(reviewed), materialized=len(by_key), out=str(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('school', choices=S.keys())
    school = ap.parse_args().school
    reviewed = Path(__file__).resolve().parents[1] / 'hierarchy' / school / 'reviewed/paper-recovery-review.json'
    print(json.dumps(materialize(reviewed, P.CODE, P.data_w('dblp-recovered.jsonl.gz', school))))


if __name__ == '__main__':
    main()
