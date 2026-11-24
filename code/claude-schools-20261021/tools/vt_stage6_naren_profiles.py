"""Admit two current Naren Ramakrishnan advisees from official VT profiles."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


ROWS = [
    ('Nikhitha Khasnavis', 'masters',
     'https://sanghani.cs.vt.edu/people/students/nikhitha-khasnavis.html',
     '2318c43f9c4c30d46d117bc988b0101c91d03da27c8473d18e534163cb8e4527',
     "Nikhitha Khasnavis is a master's of engineering degree student in the Department of Computer Science. Her advisor is Naren Ramakrishnan."),
    ('Ramachandra Rao Seethiraju', 'phd',
     'https://sanghani.cs.vt.edu/people/students/ramachandra-rao-seethiraju.html',
     'd28e552c22297a2770ae6a385b7de2d9e20c8d5a2c29056c6ef374787e027e16',
     'Ramachandra Rao Seethiraju is a Ph.D. student in the Department of Computer Science. He is advised by Naren Ramakrishnan.'),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Naren Ramakrishnan'), None)
    if rec is None:
        rec = dict(pi='Naren Ramakrishnan', students=[])
        records.append(rec)
    existing = {r['name'] for r in rec['students']}
    for name, role, url, sha, quote in ROWS:
        saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                           (url, sha)).fetchone()
        assert saved, name
        original = zlib.decompress(saved[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        assert quote in visible, name
        if name in existing:
            continue
        rec['students'].append(dict(name=name, role=role, years=[2026, 2026],
                                    years_basis='current student on VT profile captured November 2026',
                                    relationship='advising', source='vt_official_page', reviewed=True,
                                    auto=False, url=url, sha256=sha, quote=quote,
                                    note='Official VT profile explicitly names this current student and adviser.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
