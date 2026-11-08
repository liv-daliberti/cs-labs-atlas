"""R-STU-23 (owner 2026-11-08): a WashU engineering ETD's Committee Chair is the student's adviser; the rows are researched evidence."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from pihier import students as S

FILE = ROOT / 'hierarchy/washu/reviewed/thesis-committee-chair-evidence.json'


def test_R_STU_23_committee_chair_rows_are_researched_evidence():
    assert 'thesis-committee-chair-evidence.json' in S.RESEARCHED_FILES
    rows = json.loads(FILE.read_text())
    assert rows, 'no rows'
    n = 0
    for pi in rows:
        assert pi['pi']
        for s in pi['students']:
            n += 1
            assert 'Committee Chair' in s['quote']
            assert s['url'].startswith('https://repository.library.washu.edu/eng_etds/')
            assert re.fullmatch(r'[0-9a-f]{64}', s['sha256'])
            assert min(s['years']) >= 2016
            assert s['role'] in ('phd', 'masters', 'student')
            assert 'HELD' not in s.get('note', '')
    assert n >= 100
