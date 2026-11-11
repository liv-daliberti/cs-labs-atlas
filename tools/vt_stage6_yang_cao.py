"""Admit named group members from Yang Cao's VT lab page without invented dates."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/~ycao/people.html'
SHA = 'cae831149162a48a12b5df07f2568fcfab92ea49f143429518afa6bf4d3ba80f'
ROWS = [('Mansorreh Ahmadian', 'phd'), ('Rachel (Chunrui) Xu', 'phd'), ('Xiaochu Li', 'masters')]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    saved = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                       (URL, SHA)).fetchone()
    assert saved
    original = zlib.decompress(saved[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    group = visible.split('Current Group Members', 1)[1].split('Former Group Members', 1)[0]
    assert 'The PI: Dr. Young (Yang) Cao' in group
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Yang Cao'), None)
    if rec is None:
        rec = dict(pi='Yang Cao', students=[])
        records.append(rec)
    existing = {r['name'] for r in rec['students']}
    for name, role in ROWS:
        assert name in group, name
        if name in existing:
            continue
        rec['students'].append(dict(name=name, role=role, relationship='membership',
                                    source='pi_owned_page', reviewed=True, auto=False,
                                    url=URL, sha256=SHA, quote=name,
                                    note='Named in the PI-directed VT lab group. Page does not establish a calendar year or adviser relationship.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
