"""tools/content_hash.py (ROADMAP #22): a deliberate timestamp is kept but is not content."""
import hashlib
import json

import content_hash as C
import package_diff as PD
from atlas_paths import gzip_text


def write_ledger(p, stamp):
    with gzip_text(p) as f:
        for i in range(3):
            f.write(json.dumps(dict(key=f'k{i}', reason_code='x', checked_at=f'2026-11-0{stamp}T00:00:00Z')) + '\n')


def test_content_hash_ignores_the_stamp_but_not_the_content(tmp_path):
    a, b, c = (tmp_path / n / 'unavailable.jsonl.gz' for n in 'abc')
    for p in (a, b, c):
        p.parent.mkdir()
    write_ledger(a, 1); write_ledger(b, 2)
    with gzip_text(c) as f:
        f.write(json.dumps(dict(key='k0', reason_code='y', checked_at='2026-11-01T00:00:00Z')) + '\n')
    assert hashlib.sha256(a.read_bytes()).hexdigest() != hashlib.sha256(b.read_bytes()).hexdigest()     # the bytes differ ...
    assert C.content_sha256(a) == C.content_sha256(b) and C.content_sha256(a) != C.content_sha256(c)    # ... the content does not
    m1, m2 = tmp_path / 'm1' / 'MANIFEST.json', tmp_path / 'm2' / 'MANIFEST.json'
    for m, t in ((m1, 'A'), (m2, 'B')):
        m.parent.mkdir(); m.write_text(json.dumps(dict(release='r', created=t, files={})))
    assert C.content_sha256(m1) == C.content_sha256(m2)


def test_package_diff_ignores_the_same_stamps_by_default(tmp_path):
    for n, stamp in (('old', 1), ('new', 2)):
        d = tmp_path / n / 'mit'
        d.mkdir(parents=True)
        write_ledger(d / 'unavailable.jsonl.gz', stamp)
        (d / 'unavailable-summary.json').write_text(json.dumps(dict(school='mit', built_at=f'2026-11-0{stamp}', inputs=dict(copies_json=f't{stamp}', lab_papers=f't{stamp}'), papers=3)))
        (d / 'copies.json').write_text(json.dumps(dict(summary=dict(counted_at=f't{stamp}', local=2), papers={})))
    res = PD.compare_dir(tmp_path / 'old' / 'mit', tmp_path / 'new' / 'mit', PD.DEFAULT_IGNORE)
    assert {r['status'] for r in res.values()} == {'identical'}
    (tmp_path / 'new' / 'mit' / 'copies.json').write_text(json.dumps(dict(summary=dict(counted_at='t', local=3), papers={})))
    assert PD.compare_dir(tmp_path / 'old' / 'mit', tmp_path / 'new' / 'mit', PD.DEFAULT_IGNORE)['copies.json']['status'] == 'differs'
