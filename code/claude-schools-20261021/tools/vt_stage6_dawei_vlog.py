"""Admit dated VT VLOG lab members from Dawei Zhou's captured PI pages."""

import hashlib
import json

from bs4 import BeautifulSoup

import atlas_paths as P


LAB_URL = 'https://sites.google.com/view/dawei-zhou/vlog-lab'
LAB_SHA = '27fc32790bd964cb3a37827903a3358650db67d64b6dff64c9aa339820bc3124'
HOME_URL = 'https://sites.google.com/view/dawei-zhou/home'
HOME_SHA = '74dfc2003b75a5e5df5a72d98acebd0f298fd42c8ada784f3203acc528f487be'
CURRENT = [
    ('Haohui Wang', 2022, 'Haohui Wang Fall 2022 - Now'),
    ('Jianpeng Chen', 2023, 'Jianpeng Chen Fall 2023 - Now'),
    ('Tuo Wang', 2023, 'Tuo Wang Fall 2023 - Now'),
    ('Weijie Guan', 2023, 'Weijie Guan Fall 2023 - Now'),
    ('Wangzhi Zhan', 2024, 'Wangzhi Zhan Fall 202 4 - Now'),
    ('Joshua Flashner', 2024, 'Joshua Flashner Fall 202 4 - Now'),
    ('Xinyue Zeng', 2025, 'Xinyue Zeng Spring 202 5 - Now'),
    ('Binbin Cheng', 2026, 'Binbin Cheng Fall 202 6 - Now'),
    ('Cecilia Chen', 2026, 'Cecilia Chen Fall 2026 - Now'),
]
ALUMNI = [
    ('Shuaicheng Zhang', 2026, '2026: Dr. Shuaicheng Zhang'),
    ('Longfeng Wu', 2026, '2026: Dr. Longfeng Wu'),
]
ADVISED = {
    'Longfeng Wu': 'my student Longfeng Wu on passing her PhD final defense',
    'Shuaicheng Zhang': 'my student Shuaicheng Zhang on passing his PhD final defense',
}


def text_of(filename, expected):
    raw = (P.WORK / 'hierarchy/vt/reviewed/source-captures' / filename).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())


def main():
    lab = text_of('dawei-vlog-20261112.html', LAB_SHA)
    home = text_of('dawei-home-20261112.html', HOME_SHA)
    assert 'Virginia Tech VLOG Lab' in lab and 'Ph.D. Students' in lab and 'Alumni' in lab
    assert 'Dawei Zhou is an Associate Professor at the Computer Science Department of Virginia Tech' in home
    recs = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next((r for r in recs if r['pi'] == 'Dawei Zhou'), None)
    if rec is None:
        rec = dict(pi='Dawei Zhou', students=[])
        recs.append(rec)
    held_alumni = {'Fatimah Alotaibi', 'Tong Zeng', 'Adithya Kulkarni'}
    rec['students'] = [r for r in rec['students'] if r['name'] not in held_alumni]
    existing = {r['name'] for r in rec['students']}
    added = []
    for name, start, quote in CURRENT:
        assert quote in lab
        if name in existing:
            continue
        rec['students'].append(dict(
            name=name, role='phd', years=[start, 2026], years_basis='PI-owned VT lab current PhD roster, captured 2026-11-12',
            relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
            url=LAB_URL, sha256=LAB_SHA, quote=quote,
            note='The PI-owned VT lab lists this person as a current PhD student; no exclusive advising is inferred.',
        ))
        added.append(name)
    for name, year, quote in ALUMNI:
        assert quote in lab
        if name in existing:
            continue
        row = dict(
            name=name, role='phd', years=[year, year], years_basis='dated doctoral alumni on PI-owned VT lab roster',
            relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
            url=LAB_URL, sha256=LAB_SHA, quote=quote,
            note='The PI-owned VT lab lists this doctoral alumnus; no earlier start date is inferred.',
        )
        if name in ADVISED:
            assert ADVISED[name] in home
            row.update(relationship='advising', source='pi_owned_homepage',
                       url=HOME_URL, sha256=HOME_SHA, quote=ADVISED[name],
                       note='The PI explicitly calls this person his student and names a 2026 PhD final defense.')
        rec['students'].append(row)
        added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(recs, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
