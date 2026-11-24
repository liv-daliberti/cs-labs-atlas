"""Admit Kurt Luther's named current and dated alumni from his VT lab roster."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/kluther/newlab/index.html'
SHA = '06662003bf0e7ed46194e7ad77baccc9a73305a49a1faa9cdb5195576098998d'
CURRENT = ('Kirk Knutsen', 'Micah Tongen', 'William DeStaffan')
ALUMNI = (('Fei Shan', 2026), ('Anirban Mukhopadhyay', 2026), ('Matthew Wilchek', 2025),
          ('Vikram Mohanty', 2023), ('Sukrit Venkatagiri', 2022), ('Aditya Bharadwaj', 2020),
          ('Tianyi Li', 2020), ('Nai-Ching Wang', 2019))


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    stored = db.execute('select content from captures where sha256=? and status=200 limit 1', (SHA,)).fetchone()
    assert stored
    original = zlib.decompress(stored[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    assert 'directed by Dr. Kurt Luther' in visible
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Kurt Luther'), None)
    if rec is None:
        rec = dict(pi='Kurt Luther', students=[])
        records.append(rec)
    existing = {r['name']: r for r in rec['students']}
    for name in CURRENT:
        quote = f'{name} Ph.D. Student, Computer Science'
        assert quote in visible and visible.index('Graduate students') < visible.index(quote) < visible.index('Alumni')
        if name in existing:
            existing[name]['relationship'] = 'membership'
        else:
            rec['students'].append(dict(name=name, role='phd', years=[2026],
                                        years_basis='current lab roster captured 2026-11-10',
                                        relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
                                        url=URL, sha256=SHA, quote=quote,
                                        note='Current graduate-student section of the PI-directed VT lab page.'))
    for name, year in ALUMNI:
        quote = f'Dr. {name} Ph.D. CS, {year}'
        assert quote in visible and visible.index('Alumni') < visible.index(quote)
        if name in existing:
            existing[name]['relationship'] = 'membership'
        else:
            rec['students'].append(dict(name=name, role='phd', years=[year, year],
                                        years_basis='dated PhD alumni on PI-owned lab roster',
                                        relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
                                        url=URL, sha256=SHA, quote=quote,
                                        note='Dated PhD alumni section of the PI-directed VT lab page.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
