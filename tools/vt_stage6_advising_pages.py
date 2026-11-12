"""Admit bounded PI-owned VT advising and current group records."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


PAGES = [
    ('Denis Gracanin', 'https://people.cs.vt.edu/~gracanin/home/Advising.html',
     'bf7285da5fe9d755824e529cbd827eab8e5b3cb0737efaa6f7d577d5fd07aec7',
     'Current Ph.D. Students', 'Current M.S. Students', [
         ('Sikiru Adewale', 'phd', None), ('Enoch Akli', 'phd', None),
         ('Rawan Alturkistani', 'phd', None), ('Sezer Dumen', 'phd', None),
     ]),
    ('Aisling Kelliher', 'https://people.cs.vt.edu/~aislingk/mentoring.html',
     '1eb839dfa48e37b15a099bd465412a1fdab1ee0f73b7bfbe606a630e504f8c54',
     'virginia tech', 'Additional VT committees', [
         ('Neelma Bhatti', 'phd', 2022), ('Setor Zilevu', 'phd', 2022),
         ('Sai Yeshala', 'masters', 2022), ('Juliet Clark', 'masters', 2021),
         ('Yash Jain', 'masters', 2021),
     ]),
    ('Changhee Jung', 'https://people.cs.vt.edu/~chjung/',
     'b96d4a0ccabce74eb3e37c03f5fbfdc494e357d42a1327163dfb068844b8f28b',
     'Current Students', 'Alumni', [
         ('Qingrui Liu', 'phd', 2018),
     ]),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    for pi, url, sha, start, end, rows in PAGES:
        saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                           (url, sha)).fetchone()
        assert saved, url
        original = zlib.decompress(saved[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        assert pi.split(' ')[-1] in visible
        section = visible.split(start, 1)[1].split(end, 1)[0]
        rec = next((r for r in records if r['pi'] == pi), None)
        if rec is None:
            rec = dict(pi=pi, students=[])
            records.append(rec)
        existing = {s['name'] for s in rec['students']}
        for name, role, year in rows:
            if pi == 'Denis Gracanin':
                assert name in section, name
            else:
                assert name in visible.split(start, 1)[1].split('carnegie mellon university', 1)[0], name
            if name in existing:
                continue
            row = dict(name=name, role=role, relationship='advising' if pi != 'Changhee Jung' else 'membership',
                       source='pi_owned_page', reviewed=True, auto=False, url=url, sha256=sha,
                       quote=name,
                       note='PI-owned VT advising/group page lists this student; committee-only and other-institution sections excluded.')
            if year:
                row.update(years=[year, year], years_basis='dated degree on PI-owned VT page')
            rec['students'].append(row)
        print(json.dumps(dict(pi=pi, rows=len(rec['students']))))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
