"""Recover VT students missed by the lab-page extractor on two PI-owned rosters.

Each row is checked against the original captured page. These are direct
membership statements; the rows do not infer an advising relationship.
"""

import hashlib
import json
import os
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


PAGES = {
    'Chris Thomas': (
        'https://people.cs.vt.edu/chris/group/',
        '1213b7146a8ecd18ddb3a5f39373fff748b1e5cfefc8023e27d4185a68211798',
        [
            ('Md Atabuzzaman', 'phd', [2026, 2026], 'Md Atabuzzaman Ph.D. student'),
            ('Hani Alomari', 'phd', [2026, 2026], 'Hani Alomari Ph.D. student'),
            ('Kazi Mehrab', 'phd', [2026, 2026], 'Kazi Mehrab Ph.D. student, co-advised with Anuj Karpatne'),
            ('Mingsi Liao', 'phd', [2026, 2026], 'Mingsi Liao Ph.D. student, co-advised with Rebecca Cockrum'),
        ],
    ),
    'Thang Hoang': (
        'https://thanghoang.github.io/#group',
        'd72325ab775c02df681ef09014919f0cfe7bda06de349886d0eea055f189ba50',
        [
            ('Arman Riasi', 'phd', [2022, 2026], 'Arman Riasi | Fall 2022 - current'),
            ('Hoang-Dung Nguyen', 'phd', [2023, 2026], 'Hoang-Dung (Thomas) Nguyen | Spring 2023 - current'),
            ('Munshi Ala Muid', 'phd', [2023, 2026], 'Munshi Ala Muid | Fall 2023 - current | co-advise w/ Tijay Chung'),
            ('Tung Le', 'phd', [2026, 2026], 'Tung Le , PhD (2026) Dissertation'),
            ('Jacob Haltiwanger', 'masters', [2024, 2024], 'Jacob Haltiwanger , MS (2024) Thesis'),
            ('Trevor Miller', 'masters', [2023, 2023], 'Trevor Miller , MS (2023) Thesis'),
            ('Mohit Bhasi', 'masters', [2022, 2022], 'Mohit Bhasi , MS (2022) Thesis'),
        ],
    ),
}


def main():
    capture_db = os.environ.get('VT_STAGE6_CAPTURE_DB') or str(P.data('labpage-audit-captures.sqlite', 'vt'))
    db = sqlite3.connect(f'file:{capture_db}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    by_pi = {r['pi']: r for r in records}
    added = {}
    for pi, (url, sha, rows) in PAGES.items():
        saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                           (url, sha)).fetchone()
        assert saved, (pi, url)
        raw = zlib.decompress(saved[0])
        assert hashlib.sha256(raw).hexdigest() == sha
        soup = BeautifulSoup(raw, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        visible = ' '.join(soup.get_text(' ', strip=True).split())
        assert pi in visible
        assert ('Group Md Atabuzzaman' if pi == 'Chris Thomas' else 'PhD students Arman Riasi') in visible
        rec = by_pi.setdefault(pi, dict(pi=pi, students=[]))
        existing = {s['name'] for s in rec['students']}
        added[pi] = 0
        for name, role, years, quote in rows:
            assert quote in visible, (pi, name)
            if name in existing:
                continue
            rec['students'].append(dict(name=name, role=role, years=years,
                                        years_basis='current group roster' if years[-1] == 2026 else 'dated graduate entry',
                                        relationship='membership', source='pi_owned_group_roster',
                                        reviewed=True, auto=False, url=url, sha256=sha, quote=quote,
                                        note='Name and role are in the PI-owned group roster; advising is not inferred.'))
            added[pi] += 1
        if pi not in {r['pi'] for r in records}:
            records.append(rec)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(added))


if __name__ == '__main__':
    main()
