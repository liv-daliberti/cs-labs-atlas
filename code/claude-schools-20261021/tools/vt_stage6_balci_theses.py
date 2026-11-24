"""Recover Osman Balci's dated VT students from his PI-owned CV."""

import hashlib
import json
import re

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://manta.cs.vt.edu/balci/vitae.htm#Students'
SHA = '70b631f6f77af485f409c805f6e27999ba96ef6ec7845eeba44df49f4089ab34'
ROWS = [
    ('Calvin Huang', 2022, 'masters'),
    ('Gökçe Önen', 2022, 'masters'),
    ('Eman Abdelrahman', 2021, 'masters'),
    ('Zhennan Yao', 2020, 'masters'),
    ('Xuan Liu', 2019, 'masters'),
    ('Tiancheng Ying', 2019, 'masters'),
    ('S. Tuna Önder', 2018, 'masters'),
    ('Serdar Aslan', 2016, 'phd'),
]


def main():
    raw = (P.WORK / 'hierarchy/vt/reviewed/source-captures/balci-vitae-20261111.html').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    visible = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'Student Research Direction' in visible and 'Osman Balci' in visible
    section = visible.split('Student Research Direction', 1)[1]
    recs = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next((r for r in recs if r['pi'] == 'Osman Balci'), None)
    if rec is None:
        rec = dict(pi='Osman Balci', students=[])
        recs.append(rec)
    existing = {r['name'] for r in rec['students']}
    added = []
    for name, year, role in ROWS:
        marker = f'{name} ({year})'
        idx = section.find(marker)
        assert idx >= 0, marker
        suffix = section[idx:idx + 260]
        degree = 'Ph.D. Dissertation' if role == 'phd' else 'M.S. Thesis'
        match = re.search(re.escape(marker) + r'.*?' + re.escape(degree), suffix)
        assert match and 'Virginia Tech' in suffix, (name, suffix)
        quote = match.group(0)
        if name in existing:
            prior = next(r for r in rec['students'] if r['name'] == name)
            if prior.get('url') == URL:
                prior['note'] = 'The CV lists this VT thesis or dissertation under Student Research Direction; its Eman Abdelrahman entry separately names Ed Fox as co-chair.'
            continue
        rec['students'].append(dict(
            name=name, role=role, years=[year, year], years_basis='dated VT thesis/dissertation on PI-owned CV',
            relationship='advising', source='pi_owned_student_research_direction', reviewed=True, auto=False,
            url=URL, sha256=SHA, quote=quote,
            note='The CV lists this VT thesis or dissertation under Student Research Direction; its Eman Abdelrahman entry separately names Ed Fox as co-chair.',
        ))
        added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(recs, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
