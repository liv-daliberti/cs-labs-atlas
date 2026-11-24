"""Add members explicitly listed under Students on Wu-chun Feng's VT lab page."""

import hashlib
import json

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://synergy.cs.vt.edu/people.php'
SHA = 'fe62b9f8de1e3fe507b095d4269aa43593a4782815aff67f7794d5b4ed3f2886'
ROWS = [
    ('Ye Cao', 'masters', 'Ye Cao (M.S.)'),
    ('Nabayan Chaudhury', 'phd', 'Nabayan Chaudhury (Ph.D.)'),
    ('Saikat Dey', 'phd', 'Saikat Dey (Ph.D.)'),
    ('Atharva Gondhalekar', 'phd', 'Atharva Gondhalekar (Ph.D.)'),
    ('Sonal Jha', 'phd', 'Sonal Jha (Ph.D.)'),
    ('Bernard Moussad', 'phd', 'Bernard Moussad (Ph.D.)'),
    ('Ritvik Prabhu', 'masters', 'Ritvik Prabhu (M.S.)'),
    ('Rashmi Ravindranath', 'masters', 'Rashmi Ravindranath (M.S.)'),
    ('Eric Rippey', 'masters', 'Eric Rippey (M.S.)'),
    ('Niteya Shah', 'masters', 'Niteya Shah (M.S.)'),
    ('Frank Wanye', 'phd', 'Frank Wanye (Ph.D.)'),
]


def main():
    raw = (P.WORK / 'hierarchy/vt/reviewed/source-captures/synergy-people-20261112.html').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    visible = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'Synergy People Faculty & Staff Wu Feng' in visible
    student_section = visible.split(' Students ', 1)[1].split(' Collaborators (Current & Past)', 1)[0]
    assert 'Wu Feng' in visible
    recs = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next((r for r in recs if r['pi'] == 'Wu-chun Feng'), None)
    if rec is None:
        rec = dict(pi='Wu-chun Feng', students=[])
        recs.append(rec)
    existing = {r['name'] for r in rec['students']}
    added = []
    for name, role, quote in ROWS:
        assert quote in student_section, name
        if name in existing:
            continue
        rec['students'].append(dict(
            name=name, role=role, years=[2026, 2026],
            years_basis='current student section of PI-directed VT lab, captured 2026-11-12',
            relationship='membership', source='pi_owned_lab_roster', reviewed=True, auto=False,
            url=URL, sha256=SHA, quote=quote,
            note='The VT lab page names Wu Feng and lists the person in its Students section; advising is not inferred.',
        ))
        added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(recs, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
