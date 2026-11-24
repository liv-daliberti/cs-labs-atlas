"""Admit two dated VT PhDs naming Debswapna Bhattacharya as supervisor."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


ROWS = [
    ('Md. Hossain Shuvo', 2023, 'https://mdhossainshuvo.github.io',
     'cb70d99a7325a1f6f2f39988cd8951913c77627f646e9aef387cede8ce87c871',
     'Prior to joining PVAMU, I obtained my Ph.D. in Computer Science from Virginia Tech in 2023 under the supervision of Dr. Debswapna Bhattacharya .'),
    ('Rahmatullah Roche', 2024, 'https://rahmatullah-roche.github.io',
     'eb5ab6f95c59ae7518ee21b5179143356bfb3f7651c73e49af09b39052d2f273',
     'Prior to joining Columbus State University, I obtained my Ph.D. in Computer Science from Virginia Tech in 2024 under the supervision of Dr. Debswapna Bhattacharya'),
]


def main():
    source = P.data('labpage-audit-captures.sqlite', 'vt')
    db = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    rec = next((r for r in records if r['pi'] == 'Debswapna Bhattacharya'), None)
    if rec is None:
        rec = dict(pi='Debswapna Bhattacharya', students=[])
        records.append(rec)
    existing = {r['name']: r for r in rec['students']}
    for name, year, url, sha, quote in ROWS:
        page = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                          (url, sha)).fetchone()
        assert page, (name, url)
        original = zlib.decompress(page[0])
        assert hashlib.sha256(original).hexdigest() == sha
        visible = ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())
        assert quote in visible, name
        if name in existing:
            existing[name]['sha256'] = sha
            continue
        rec['students'].append(dict(name=name, role='phd', years=[year, year],
                                    years_basis='student-owned page states VT PhD year',
                                    relationship='advising', source='student_owned_page', reviewed=True, auto=False,
                                    url=url, sha256=sha, quote=quote,
                                    note='The student explicitly names the VT PhD year and this PI as supervisor.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(pi=rec['pi'], rows=len(rec['students']))))


if __name__ == '__main__':
    main()
