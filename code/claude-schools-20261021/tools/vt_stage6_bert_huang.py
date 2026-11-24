"""Admit four dated, official VT student-adviser records for Bert Huang."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


ROWS = [
    ('Elaheh Raisi', 'phd', 2019,
     'https://sanghani.cs.vt.edu/people/students/elaheh-raisi.html',
     'c5e1680d8558ec89e6ff20e2a9923d5fd2c9e763c65a14fdc0337ab99c0d06ba',
     'Her advisor was Bert Huang and she worked at the Machine Learning Lab.'),
    ('Walid Chaabene', 'masters', None,
     'https://sanghani.cs.vt.edu/people/students/walid-chaabene.html',
     '9af2b4e26ed057e4d6e613e05dd462023fb431a83c2c7affab3be4546f5a5181',
     'His advisor was Bert Huang and he worked at the Machine Learning Lab.'),
    ('Shuangfei Fan', 'phd', 2019,
     'https://sanghani.cs.vt.edu/news/2019/congratulations-dac-summer-fall-2019-graduates.html',
     'f32aed125b8079dda0a53d99d189ed3b2789b48ad9339467947861bc70d4294a',
     'Shuangfei Fan , advised by Bert Huang , received a Ph.D. in computer science.'),
    ('Reid Bixler', 'masters', 2018,
     'https://sanghani.cs.vt.edu/news/2018/congratulations-dac-spring-summer-graduates.html',
     '75a1a32dc0c7c7f58102124bec14f461f8591bce751c5870078ecce9460c4396',
     'Reid Bixler , advised by Bert Huang, received a master’s degree in computer science and applications.'),
]


def main():
    source = P.data('labpage-audit-captures.sqlite', 'vt')
    db = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Bert Huang'), None)
    if rec is None:
        rec = dict(pi='Bert Huang', students=[])
        records.append(rec)
    existing = {r['name']: r for r in rec['students']}
    for name, role, year, url, sha, quote in ROWS:
        page = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                          (url, sha)).fetchone()
        assert page, (name, url)
        original = zlib.decompress(page[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        assert quote in visible, name
        if name in existing:
            continue
        row = dict(name=name, role=role, relationship='advising', source='vt_official_page',
                   reviewed=True, auto=False, url=url, sha256=sha, quote=quote,
                   note='Official Virginia Tech source explicitly names Bert Huang as adviser.')
        if year is not None:
            row.update(years=[year, year], years_basis='official VT graduation story or student page')
        rec['students'].append(row)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
