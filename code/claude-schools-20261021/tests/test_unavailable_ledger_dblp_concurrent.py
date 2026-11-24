"""Concurrent school ledgers must not share the DBLP scan scratch file."""
import gzip
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import dblp_ee
import unavailable_ledger as U


def test_concurrent_school_scans_use_distinct_scratch_files(monkeypatch, tmp_path):
    monkeypatch.setattr(U, 'RAW', tmp_path)
    barrier = Barrier(2)
    seen, lock = [], Lock()

    def scan(extra, out, only_extra):
        assert only_extra and len(extra) == 1
        with lock:
            seen.append(out)
        barrier.wait(timeout=5)
        part = out.with_suffix('.part')
        with gzip.open(part, 'wt') as f:
            f.write(json.dumps(dict(paper=extra[0]['key'], dblp_key='conf/test/1', rule='doi', year=2024, ee=[])) + '\n')
        part.replace(out)

    monkeypatch.setattr(dblp_ee, 'scan', scan)

    def run(school):
        p = dict(key='paper', doi='10.1/test', r=dict(doi='10.1/test', title='A paper title long enough', year=2024,
                                                  byline=['A Researcher'], pis=['A Researcher']))
        return U.src_dblp({school: [p]}, offline=False, n=Counter())[school]['paper']

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ('alpha', 'beta')))

    assert len(seen) == len(set(seen)) == 2
    assert [r['result'] for r in results] == ['none', 'none']
    assert not list(tmp_path.glob('ledger_dblp_scan_*'))
    assert (tmp_path / 'ledger_dblp_alpha.jsonl.gz').exists()
    assert (tmp_path / 'ledger_dblp_beta.jsonl.gz').exists()
