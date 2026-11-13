"""Recover VT Notification Systems Lab students from its PI-linked group page."""

import hashlib
import json
import re

from bs4 import BeautifulSoup

import atlas_paths as P


HOME_URL = 'https://people.cs.vt.edu/~mccricks/'
HOME_SHA = 'f7a0fe3e42c597b18f7a865621bc4803bc69bab6e5d0a34388a4961469642152'
GROUP_URL = 'https://research.cs.vt.edu/ns/'
GROUP_SHA = '433e545999d3b36304a4c1e6765978f10f32b3852589b29b55c91e6904991df1'
CURRENT = ['Derek Haqq', 'Yusheng Cao', 'Wei-Lu Wang', 'John Zhao', 'Kirk Knutsen']
PHD = [
    ('Jixiang Fan', 2026), ('Morva Saaty', 2026), ('Taha Hassan', 2024),
    ('Neelma Bhatti', 2022), ('Lindah Kotut', 2021), ('Shuo Niu', 2019),
    ('Andrey Esakia', 2018), ('Elefelious Getachew Belay', 2017), ('Mohammed Seyam', 2017),
]
MASTERS = [
    ('Natalie Andrus', 2025), ('Mary Kate McGranahan', 2025),
    ('Jaitun Patel', 2023), ('Navyaram Kondur', 2018),
]


def text_of(filename, sha):
    raw = (P.WORK / 'hierarchy/vt/reviewed/source-captures' / filename).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())


def main():
    home = text_of('mccrickard-home-20261112.html', HOME_SHA)
    group = text_of('mccrickard-group-20261112.html', GROUP_SHA)
    assert 'SCOTT MCCRICKARD' in home.upper() and 'Virginia Tech' in home
    assert 'research group page' in home
    assert 'Notification Systems Lab Students and Alumni' in group
    current, rest = group.split('Current students', 1)[1].split('PhD Alumni', 1)
    phd, rest = rest.split('MS Alumni', 1)
    masters = rest.split('Undergraduates', 1)[0]
    recs = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next((r for r in recs if r['pi'] == 'Scott McCrickard'), None)
    if rec is None:
        rec = dict(pi='Scott McCrickard', students=[])
        recs.append(rec)
    existing = {r['name'] for r in rec['students']}
    added = []
    for name in CURRENT:
        assert name in current, name
        if name in existing:
            continue
        rec['students'].append(dict(
            name=name, role='student', years=[2026, 2026],
            years_basis='current student section on PI-linked VT lab page, captured 2026-11-12',
            relationship='membership', source='pi_linked_group_roster', reviewed=True, auto=False,
            url=GROUP_URL, sha256=GROUP_SHA, quote=name,
            note='The PI links this lab page. Degree and exclusive advising are not stated for the current student.',
        ))
        added.append(name)
    for role, rows, section in [('phd', PHD, phd), ('masters', MASTERS, masters)]:
        for name, year in rows:
            match = re.search(re.escape(name) + r'.*?Date of defense: ' + str(year) + r'-\d\d-\d\d', section)
            assert match, name
            if name in existing:
                continue
            rec['students'].append(dict(
                name=name, role=role, years=[year, year], years_basis='dated defense on PI-linked VT lab alumni page',
                relationship='membership', source='pi_linked_group_roster', reviewed=True, auto=False,
                url=GROUP_URL, sha256=GROUP_SHA, quote=match.group(0),
                note='The PI-linked VT group page lists this dated degree alumnus; exclusive advising is not inferred.',
            ))
            added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(recs, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
