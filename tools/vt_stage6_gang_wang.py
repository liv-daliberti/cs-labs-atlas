"""Record the dated VT alumnus on Gang Wang's own student page."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/gangwang/students.html'
SHA = 'fee6ddddc45667ccb65f9b828c5733ae2fba552caa21825948860ae041558ab2'
QUOTE = 'Alumni Chun Wang (MS VT, 2018) >> IBM'


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    result = db.execute('select content from captures where sha256=? and status=200 limit 1', (SHA,)).fetchone()
    assert result
    original = zlib.decompress(result[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    assert 'Gang Wang Students' in visible and QUOTE in visible
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Gang Wang'), None)
    if rec is None:
        rec = dict(pi='Gang Wang', students=[])
        records.append(rec)
    if not any(r['name'] == 'Chun Wang' for r in rec['students']):
        rec['students'].append(dict(name='Chun Wang', role='masters', years=[2018, 2018],
                                    years_basis='PI-owned student page states MS VT, 2018',
                                    relationship='membership', source='pi_owned_student_page',
                                    reviewed=True, auto=False, url=URL, sha256=SHA, quote=QUOTE,
                                    note='The 2018 VT MS alumnus is listed on this PI’s own student page during the PI’s 2016–2019 VT appointment.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
