"""Admit dated current students from Na Meng's own Virginia Tech group page."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/nm8247/'
SHA = 'c774affa3438214a5b69457c3968ef99442d6ac9ef24784fd6d62aa019ce8146'
ROWS = [
    ('Ye Cao', 'masters', 2025, 'Ye Cao (MS student, Spring 2025 - )'),
    ('Xiaoyan Zang', 'masters', 2025, 'Xiaoyan Zang (MS student, Fall 2025 - )'),
    ('Shakir Farhan Mohammed', 'masters', 2025, 'Shakir Farhan Mohammed (MS student, Fall 2025 - )'),
    ('Shrikar Reddy Kota', 'masters', 2026, 'Shrikar Reddy Kota (MS student, Spring 2026 - )'),
    ('Joohyun Park', 'phd', 2026, 'Joohyun Park (PhD student, Fall 2026 - )'),
    ('Nabin Adhikari', 'masters', 2026, 'Nabin Adhikari (MS student, Summer 2026 - )'),
    ('Jai Kumar Sharma', 'masters', 2026, 'Jai Kumar Sharma (MS student, Fall 2026 - )'),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                       (URL, SHA)).fetchone()
    assert saved
    original = zlib.decompress(saved[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    assert 'Na Meng' in visible and 'Current Students' in visible
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Na Meng'), None)
    if rec is None:
        rec = dict(pi='Na Meng', students=[])
        records.append(rec)
    existing = {r['name'] for r in rec['students']}
    for name, role, year, quote in ROWS:
        assert quote in visible, name
        if name in existing:
            continue
        rec['students'].append(dict(name=name, role=role, years=[year, 2026],
                                    years_basis='dated current-student entry on PI-owned VT page',
                                    relationship='membership', source='pi_owned_page', reviewed=True, auto=False,
                                    url=URL, sha256=SHA, quote=quote,
                                    note='Current student named on Na Meng\'s VT group page; adviser claim withheld.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
