"""Admit explicit thesis-chair/adviser relations from VT CS highlights."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


SOURCES = [
    ('https://people.cs.vt.edu/ribbens/d/highlights/2018Q2.html',
     'fa1b1aa9178e6e3e8b5e8ff388fcb46eedb80ec57f6367ad7a4d94a5858896bb', [
         ('Madhav Marathe', 'Ahmed Abdelnaeim Elbery', 2018,
          'Ahmed Abdelnaeim Elbery, "Large-Scale Modeling of Smart Cities Considering the Mutual Impact of Transportation and Communication Systems," Marathe (co-chair with Rakha)'),
         ('Ali Butt', 'Ali Anwar', 2018,
          'Ali Anwar, "Towards Efficient and Flexible Object Storage Using Resource and Functional Partitioning," Butt (chair)'),
     ]),
    ('https://people.cs.vt.edu/ribbens/d/highlights/2024Q2.html',
     'ffa376278b5b8202ec4ae808fd47d137666cbb1dd3fa604b1f2cc21d05837ae3', [
         ('Jin-Hee Cho', 'Qi Zhang', 2025,
          'PhD student Qi Zhang received the best research short paper award at CAPWIC 2025. Qi is advised by Jin-Hee Cho.'),
     ]),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    for url, sha, items in SOURCES:
        saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                           (url, sha)).fetchone()
        assert saved, url
        original = zlib.decompress(saved[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        for pi, name, year, quote in items:
            assert quote in visible, name
            rec = next((r for r in records if r['pi'] == pi), None)
            if rec is None:
                rec = dict(pi=pi, students=[])
                records.append(rec)
            if any(s['name'] == name for s in rec['students']):
                continue
            rec['students'].append(dict(name=name, role='phd', years=[year, year],
                                        years_basis='dated VT CS highlight', relationship='advising',
                                        source='vt_cs_highlights', reviewed=True, auto=False,
                                        url=url, sha256=sha, quote=quote,
                                        note='Official VT CS highlight explicitly names thesis chair or adviser.'))
            print(json.dumps(dict(pi=pi, student=name)))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
