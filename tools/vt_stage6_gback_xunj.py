"""Admit dated thesis students on Godmar Back and Xun Jian VT pages."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


PAGES = [
    ('Godmar Back', 'https://people.cs.vt.edu/~gback/',
     'a13ce88789e932c22e8f7ba771f0a2692a474a720077ebb96731be5d97cb803c', [
         ('Eric Williamson', 'masters', 2018, 'Eric Williamson MS, 2018.'),
         ('William Naciri', 'masters', 2017, 'William Naciri MS, 2017.'),
         ('Lance Chao', 'masters', 2016, 'Lance Chao MS, 2016.'),
     ]),
    ('Xun (Steve) Jian', 'https://people.cs.vt.edu/xunj/Students.html',
     '72c9b76045c7b67f686eb69986d000e91a66501723ab91bb327ba5daaef8492f', [
         ('Muhammad Laghari', 'phd', 2025, 'Muhammad Laghari , PhD, 2025.'),
         ('Xin Wang', 'phd', 2025, 'Xin Wang, PhD, 2025.'),
         ('Gagandeep Panwar', 'phd', 2024, 'Gagandeep Panwar, PhD, 2024.'),
         ('Da Zhang', 'phd', 2023, 'Da Zhang : PhD, 2023.'),
     ]),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    for pi, url, sha, rows in PAGES:
        saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                           (url, sha)).fetchone()
        assert saved, url
        original = zlib.decompress(saved[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        assert pi.split(' ')[0] in visible and 'Students' in visible
        rec = next((r for r in records if r['pi'] == pi), None)
        if rec is None:
            rec = dict(pi=pi, students=[])
            records.append(rec)
        existing = {r['name'] for r in rec['students']}
        for name, role, year, quote in rows:
            assert quote in visible, name
            if name in existing:
                continue
            rec['students'].append(dict(name=name, role=role, years=[year, year],
                                        years_basis='dated thesis/degree on PI-owned VT student page',
                                        relationship='membership', source='pi_owned_page', reviewed=True,
                                        auto=False, url=url, sha256=sha, quote=quote,
                                        note='PI-owned VT student page lists dated degree; academic adviser claim withheld.'))
        print(json.dumps(dict(pi=pi, rows=len(rec['students']))))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
