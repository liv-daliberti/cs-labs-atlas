"""Admit VT Echolab members and a named Wenjing Lou advisee."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


ECHO_URL = 'https://echolab.cs.vt.edu/members/'
ECHO_SHA = '4b6e712e4e712c437c7385de851681c115db937269cf8deb1b38136eb0102afe'
AMAZON_URL = 'https://amazon.cs.vt.edu/'
AMAZON_SHA = '25ebf9808c29ab996b7e6df801c9fe207f1124211286d99479532b7e8167d266'
ECHO = [
    ('Adnan Abbas', 'phd'), ('Andrew Jelson', 'phd'), ('Caleb Wohn', 'phd'),
    ('Carlos Augusto Bautista Isaza', 'phd'), ('Daniel Manesh', 'phd'),
    ('Jaehoon Pyun', 'phd'), ('Sangwook Lee', 'phd'), ('Xinyi Zhang', 'phd'),
    ('Yuhang Zheng', 'masters'),
]


def saved_visible(db, url, sha):
    row = db.execute('select content from captures where url=? and status=200 and sha256=? limit 1',
                     (url, sha)).fetchone()
    assert row, url
    original = zlib.decompress(row[0])
    assert hashlib.sha256(original).hexdigest() == sha
    return ' '.join(BeautifulSoup(original, 'html.parser').get_text(' ', strip=True).split())


def main():
    db = sqlite3.connect(f'file:{P.data("labpage-audit-captures.sqlite", "vt")}?mode=ro', uri=True)
    echo = saved_visible(db, ECHO_URL, ECHO_SHA)
    amazon = saved_visible(db, AMAZON_URL, AMAZON_SHA)
    assert 'Director Sang Won Lee' in echo
    path = P.data_w('few-students-evidence.json', 'vt')
    records = json.loads(path.read_text())
    for pi in ('Sang Won Lee', 'Wenjing Lou'):
        if not any(r['pi'] == pi for r in records):
            records.append(dict(pi=pi, students=[]))
    by_pi = {r['pi']: r for r in records}
    current = echo.split('Ph.D. students', 1)[1].split('Undergraduate students', 1)[0]
    for name, role in ECHO:
        quote = f'{name} (Computer Science, Virginia Tech)'
        assert quote in current, name
        rec = by_pi['Sang Won Lee']
        if any(x['name'] == name for x in rec['students']):
            continue
        rec['students'].append(dict(name=name, role=role, years=[2026, 2026],
                                    years_basis='current-members listing captured November 2026',
                                    relationship='membership', source='lab_page', reviewed=True, auto=False,
                                    url=ECHO_URL, sha256=ECHO_SHA, quote=quote,
                                    note='Named on PI-directed Echolab VT current-member page; adviser claim withheld.'))
    quote = 'Shahriar is advised by Wenjing Lou.'
    assert 'Md Hasan Shahriar, Ph.D. student in the Department of Computer Science.' in amazon
    assert quote in amazon
    rec = by_pi['Wenjing Lou']
    if not any(x['name'] == 'Md Hasan Shahriar' for x in rec['students']):
        rec['students'].append(dict(name='Md Hasan Shahriar', role='phd', years=[2026, 2026],
                                    years_basis='current VT program page captured November 2026',
                                    relationship='advising', source='vt_official_page', reviewed=True,
                                    auto=False, url=AMAZON_URL, sha256=AMAZON_SHA, quote=quote,
                                    note='Official VT initiative explicitly names this current PhD and adviser.'))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({pi: len(by_pi[pi]['students']) for pi in ('Sang Won Lee', 'Wenjing Lou')}))


if __name__ == '__main__':
    main()
