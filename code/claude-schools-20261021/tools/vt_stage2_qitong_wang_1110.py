"""Resolve Qitong Wang's DBLP VT affiliation as a student-era connection."""

import hashlib
import json

import requests

import atlas_paths as P


def main():
    url = 'https://wqtwjt1996.github.io/'
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    raw = response.content
    body = raw.decode('utf-8', 'replace')
    for marker in ('Qitong Wang', 'Ph.D. candidate', 'University of Delaware',
                   'Christopher Rasmussen', 'When One Modality Rules Them All'):
        assert marker in body, marker
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'qitong-wang-home.html'
    saved.write_bytes(raw)
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Qitong Wang'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=[], source='dblp_affiliation', decision='not_faculty_listed',
        reason=('The candidate DBLP PID has the distinctive publication on this first-party '
                'Qitong Wang site. The site identifies him as a University of Delaware PhD '
                'candidate advised by Christopher Rasmussen since 2021, following a Boston '
                'University MS. Its dated education sequence and the former VT DBLP affiliation '
                'do not establish a VT professor-rank appointment in the census window.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/219/2237-1'], dblp_window=13,
                      affiliation_notes=['University of Delaware, Department of Computer and Information Sciences, DE, USA',
                                         'Virginia Tech, VA, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(), raw_path=str(saved.relative_to(P.ROOT)),
            observed='2026-11-10', quote=('Qitong Wang; final-year Ph.D. candidate in the Department '
                'of Computer and Information Sciences at the University of Delaware; advised by Christopher Rasmussen'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment or a distinct namesake is identified.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Qitong Wang first-party student identity')


if __name__ == '__main__':
    main()
