"""Admit five dated students explicitly listed on Cliff Shaffer's own thesis page."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/~shaffer/students.html'
SHA = 'a24a7a46e1dab2b6b95d0a988481271b54ea6e126ec8d38e92f9acaa016d237c'
ROWS = [
    ('Rifat Sabbir Mansur', 'phd', 2025, 'Rifat Sabbir Mansur, Towards Improving Students\' Software Testing Practices using Modified Mutation Testing , PhD Dissertation, April 2025.'),
    ('Molly Domino', 'phd', 2024, 'Molly Domino, Self-Regulated Learning Skills Research in Computer Science: The State of the Field , PhD Dissertation, August 2024.'),
    ('Yusuf Elnady', 'masters', 2022, 'Yusuf Elnady, Detecting Credit-Seeking Behavior on Programmed Instruction Framesets , MS Thesis, May 2022.'),
    ('Samnyeong Heo', 'masters', 2022, 'Samnyeong Heo, Analyzing Student Session Data in an eTextbook , MS Thesis, May 2022.'),
    ('Jieun Chon', 'masters', 2019, 'Jieun Chon, Interactive Visualization for Novice Learners , MS Thesis, July 2019.'),
]


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    result = db.execute('select content from captures where sha256=? and status=200 limit 1', (SHA,)).fetchone()
    assert result
    original = zlib.decompress(result[0])
    assert hashlib.sha256(original).hexdigest() == SHA
    visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
    assert 'The following is a list of Phd Dissertations and MS Theses for my students' in visible
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Cliff Shaffer'), None)
    if rec is None:
        rec = {'pi': 'Cliff Shaffer', 'students': []}
        records.append(rec)
    existing = {r['name'] for r in rec['students']}
    for name, role, year, quote in ROWS:
        assert quote in visible, name
        if name in existing:
            continue
        rec['students'].append(dict(name=name, role=role, years=[year, year],
                                    years_basis='dated thesis on PI-owned page', relationship='advising',
                                    source='pi_owned_thesis_list', reviewed=True, auto=False,
                                    url=URL, sha256=SHA, quote=quote,
                                    note='The page introduction explicitly calls these the PI’s students; the row states the degree and date.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
