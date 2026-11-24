"""Recover VT SPIN lab members from Shaddi Hasan's captured student page."""

import hashlib
import json

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://www.shaddih.com/'
SHA = 'de1d7ffff39aeb72f2163111c67d5c4f0941915d3287203e5ffd35dd061d5df8'
CURRENT = [
    ('Wesley Woo', 'phd', 'Wesley Woo PhD'),
    ('Tauhid Nabi', 'phd', 'Tauhid Nabi PhD'),
    ('Aatif Dar', 'phd', 'Aatif Dar PhD'),
    ('Prashiddha Dhoj Thapa', 'phd', 'Prashiddha Dhoj Thapa PhD'),
]
ALUMNI = [
    ('Zhuowei Wen', 'masters', 2025, 'Zhuowei Wen MS 2025'),
    ('Zahra Yazdani', 'undergraduate', 2023, 'Zahra Yazdani BS 2023'),
    ('Molly Hickman', 'masters', 2022, 'Molly Hickman MS 2022'),
]


def main():
    raw = (P.WORK / 'hierarchy/vt/reviewed/source-captures/shaddi-spin-20261112.html').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    visible = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'I am an assistant professor of computer science at Virginia Tech' in visible
    assert 'I am lucky to work with excellent students as part of the Systems, People, Infrastructure, and Networks (SPIN) Lab.' in visible
    assert 'Last updated August 2026' in visible
    student_section = visible.split('I am lucky to work with excellent students as part of the Systems, People, Infrastructure, and Networks (SPIN) Lab.', 1)[1].split(' Teaching ', 1)[0]
    assert 'Alumni Monniiesh Velmurugan MS 2026' in student_section
    recs = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next((r for r in recs if r['pi'] == 'Shaddi Hasan'), None)
    if rec is None:
        rec = dict(pi='Shaddi Hasan', students=[])
        recs.append(rec)
    existing = {r['name'] for r in rec['students']}
    added = []
    for name, role, quote in CURRENT:
        assert quote in student_section.split(' Alumni ', 1)[0]
        if name in existing:
            continue
        rec['students'].append(dict(
            name=name, role=role, years=[2026, 2026],
            years_basis='current VT SPIN lab student section, page says updated August 2026',
            relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
            url=URL, sha256=SHA, quote=quote,
            note='The PI states these people are in his VT lab; no exclusive advising is inferred.',
        ))
        added.append(name)
    for name, role, year, quote in ALUMNI:
        assert quote in student_section.split(' Alumni ', 1)[1]
        if name in existing:
            continue
        rec['students'].append(dict(
            name=name, role=role, years=[year, year],
            years_basis='dated SPIN lab alumni entry',
            relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
            url=URL, sha256=SHA, quote=quote,
            note='The PI-owned VT lab lists this dated alumnus. Monniiesh Velmurugan is held because the page describes a December 2026 graduation after the capture date.',
        ))
        added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(recs, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
