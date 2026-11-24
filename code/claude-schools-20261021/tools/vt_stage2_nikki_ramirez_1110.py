"""Resolve Nikki Ramirez-Saffy's VT student role from her coauthored paper."""

import hashlib
import json
import subprocess

import requests

import atlas_paths as P


def main():
    url = 'https://agiovannelli.github.io/publications/tvcg25-wild.pdf'
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    raw = response.content
    assert raw.startswith(b'%PDF')
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'nikki-ramirez-saffy-tvcg25.pdf'
    saved.write_bytes(raw)
    text = ' '.join(subprocess.check_output(['pdftotext', '-layout', str(saved), '-'], text=True).split())
    assert 'Nikki Ramirez-Saffy is a PhD student' in text
    assert 'Virginia Tech' in text
    assert 'Working in Extended Reality in the Wild' in text
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Gabriella N. Ramirez'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['G. Nikki Ramirez-Saffy', 'G. Nikki Ramirez'],
        source='dblp_affiliation', decision='not_faculty_listed',
        reason=('An author biography on a first-party 2025 paper identifies G. Nikki Ramirez-Saffy '
                'as a Virginia Tech computer-science PhD student. Her DBLP aliases include this '
                'publication name. No VT professor-rank appointment in the 2016–2026 window is established.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/347/3179'], dblp_window=7,
                      affiliation_notes=['Virginia Tech, Blacksburg, VA, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(),
            raw_path=str(saved.relative_to(P.ROOT)), observed='2026-11-10',
            quote=('G. Nikki Ramirez-Saffy is a PhD student in the Department of Computer Science at Virginia Tech'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Nikki Ramirez-Saffy VT doctoral-student role')


if __name__ == '__main__':
    main()
