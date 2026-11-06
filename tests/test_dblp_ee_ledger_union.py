"""dblp_ee.step also reads raw/ledger_dblp_<school>.jsonl.gz (2026-11-06): the step's own cache covers the six old schools only."""
import gzip
import json
from collections import Counter, defaultdict

import dblp_ee
import ftp_common as F


def test_step_unions_the_ledger_scan_of_the_school(tmp_path, monkeypatch):
    cache = tmp_path / 'dblp_ee_matches.jsonl.gz'
    with gzip.open(cache, 'wt') as f:
        f.write('')
    with gzip.open(tmp_path / 'ledger_dblp_xx.jsonl.gz', 'wt') as f:
        f.write(json.dumps(dict(paper='W1', dblp_key='conf/usenix/A24', rule='doi', year=2024, ee=['https://www.usenix.org/conference/x/presentation/a'])) + '\n')
    monkeypatch.setattr(dblp_ee, 'CACHE', cache)
    monkeypatch.setattr(F.P, 'FT_RAW', tmp_path, raising=False)
    n = Counter()
    miss = [(dict(work='W1', oa='W1'), 'w1')]
    rows = dblp_ee.step('xx', miss, defaultdict(set), n, lambda k: False)
    assert [r['url'] for r in rows] == ['https://www.usenix.org/conference/x/presentation/a'] and n['dblp_records:doi'] == 1
