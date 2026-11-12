"""Record the VT doctoral student explicitly placed in Onufriev's lab by VT News."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://news.vt.edu/articles/2026/06/eng-cs-nih-hidden-architecture-of-dna.html'
SHA = 'e1e3e149b1ae90a449d9708bea14f0835c1ed6d3f2bfc087dc118196494ea3a9'
QUOTE = "Charles Plate, a doctoral student in chemical engineering., work in Alexey Onufriev's lab on DNA-related projects."


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    stored = db.execute('select content from captures where sha256=? and status=200 limit 1', (SHA,)).fetchone()
    assert stored
    original = zlib.decompress(stored[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    assert QUOTE in visible
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Alexey Onufriev'), None)
    if rec is None:
        rec = dict(pi='Alexey Onufriev', students=[])
        records.append(rec)
    if not any(r['name'] == 'Charles Plate' for r in rec['students']):
        rec['students'].append(dict(name='Charles Plate', role='phd', years=[2026],
                                    years_basis='official university news dated 2026-06',
                                    relationship='membership', source='official_university_news',
                                    reviewed=True, auto=False, url=URL, sha256=SHA, quote=QUOTE,
                                    note='VT News identifies this chemical-engineering doctoral student as working in this PI lab; it does not state this PI is the academic adviser.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
