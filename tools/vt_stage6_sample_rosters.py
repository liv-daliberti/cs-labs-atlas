"""Recover dated students on two PI-owned VT pages in the Stage 6 sample."""

import hashlib
import json
import re

from bs4 import BeautifulSoup

import atlas_paths as P


SOURCES = {
    'Bimal Viswanath': (
        'https://people.cs.vt.edu/vbimal/#students',
        '4f09a2a2709e867a0cb4fc156d19fbf2db288d92d0faedaa6cd5048f772f4fe4',
        'bimal-students-20261111.html',
        [
            ('Xavier Pleimling', 'phd', 2024, 2026, 'current', 'Xavier Pleimling (Fall 2024 - Present)'),
            ('Sifat Muhammad Abdullah', 'phd', 2025, 2025, 'alumni', 'Sifat Muhammad Abdullah (2025)'),
            ('Jiameng Pu', 'phd', 2022, 2022, 'alumni', 'Jiameng Pu (2022)'),
            ('Steve T.K. Jan', 'phd', 2020, 2020, 'alumni', 'Steve T.K. Jan (2020, co-advised with Gang Wang)'),
            ('Nicholas Kong', 'masters', 2024, 2024, 'alumni', 'Nicholas Kong (2024)'),
            ('Connor Weeks', 'masters', 2023, 2023, 'alumni', 'Connor Weeks (2023)'),
            ('Cristian Vives', 'masters', 2022, 2022, 'alumni', 'Cristian Vives (2022)'),
            ('Ahmadreza Azizi', 'masters', 2020, 2020, 'alumni', 'Ahmadreza Azizi (2020)'),
            ('Tianrui Hu', 'masters', 2020, 2020, 'alumni', 'Tianrui Hu (2020, co-advised with Gang Wang)'),
            ('Neal Mangaokar', 'undergraduate', 2020, 2020, 'alumni', 'Neal Mangaokar (2020)'),
            ('Lauren Kelly', 'undergraduate', 2020, 2020, 'alumni', 'Lauren Kelly (2020)'),
        ],
    ),
    'Lenwood S. Heath': (
        'https://people.cs.vt.edu/~heath/students/',
        '87528c3a9fe6661f4f5eae598b20e44b7855f0cd1f41964cb7eb404fcebfb368',
        'heath-students-20261111.html',
        [
            ('Doaa Abdelsalam Ahmed Mohamed Altarawy', 'phd', 2017, 2017, 'alumni', 'Doaa Abdelsalam Ahmed Mohamed Altarawy (2017)'),
            ('Badhan Das', 'phd', 2026, 2026, 'alumni', 'Badhan Das (2026)'),
            ('Fatma Elzahraa Sobhy Eid', 'phd', 2017, 2017, 'alumni', 'Fatma Elzahraa Sobhy Eid (2017)'),
            ('Haitham Abdulrahman Elmarakeby', 'phd', 2017, 2017, 'alumni', 'Haitham Abdulrahman Elmarakeby (2017)'),
            ('Siddharth Krishnan', 'phd', 2018, 2018, 'alumni', 'Siddharth Krishnan (2018)'),
            ('Hanaa A. Torkey', 'phd', 2017, 2017, 'alumni', 'Hanaa A. Torkey (2017)'),
            ('Andrew Scott Warren', 'phd', 2017, 2017, 'alumni', 'Andrew Scott Warren (2017)'),
            ('Jingyi (Eve) Zhang', 'phd', 2026, 2026, 'alumni', 'Jingyi (Eve) Zhang (2026)'),
            ('Atul Bharadwaj', 'masters', 2025, 2025, 'alumni', 'Atul Bharadwaj (2025)'),
            ('Ashkan Nazari', 'masters', 2021, 2021, 'alumni', 'Ashkan Nazari (2021)'),
            ('Chandra Sekhar Nerella', 'masters', 2024, 2024, 'alumni', 'Chandra Sekhar Nerella (2024)'),
            ('Ying Ni', 'masters', 2016, 2016, 'alumni', 'Ying Ni (2016)'),
            ('Aarathi Raghuraman', 'masters', 2021, 2021, 'alumni', 'Aarathi Raghuraman (2021)'),
            ('Jeffrey A. Robertson', 'masters', 2018, 2018, 'alumni', 'Jeffrey A. Robertson (2018)'),
            ('Rathna Senthil', 'masters', 2016, 2016, 'alumni', 'Rathna Senthil (2016)'),
            ('Yanshen Yang', 'masters', 2018, 2018, 'alumni', 'Yanshen Yang (2018)'),
        ],
    ),
}


def main():
    records = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    by_pi = {r['pi']: r for r in records}
    added = {}
    for pi, (url, sha, filename, rows) in SOURCES.items():
        capture = P.WORK / 'hierarchy/vt/reviewed/source-captures' / filename
        raw = capture.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == sha
        soup = BeautifulSoup(raw, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        visible = ' '.join(soup.get_text(' ', strip=True).split())
        assert pi.split()[-1] in visible
        if pi == 'Bimal Viswanath':
            assert 'Current Students PhD Students' in visible
            assert 'Alumni PhD Graduates' in visible
        else:
            assert 'My Students PhD Graduates' in visible
            assert 'Masters Thesis Graduates' in visible
        rec = by_pi.setdefault(pi, dict(pi=pi, students=[]))
        old = {x['name'] for x in rec['students']}
        added[pi] = 0
        for name, role, start, end, section, quote in rows:
            assert ' '.join(quote.split()) in visible, (pi, name)
            assert re.search(r'\b20\d\d\b', quote)
            if name in old:
                if role == 'undergraduate':
                    next(x for x in rec['students'] if x['name'] == name)['relationship'] = 'membership'
                continue
            rec['students'].append(dict(
                name=name, role=role, years=[start, end],
                years_basis='dated current roster' if section == 'current' else 'dated graduate on PI-owned roster',
                relationship='membership' if section == 'current' or role == 'undergraduate' else 'advising',
                source='pi_owned_student_page', reviewed=True, auto=False,
                url=url, sha256=sha, quote=quote,
                note='The PI-owned VT page names the student in a degree-specific section. No earlier start or exclusive advising is inferred.',
            ))
            added[pi] += 1
        if pi not in {r['pi'] for r in records}:
            records.append(rec)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(added))


if __name__ == '__main__':
    main()
