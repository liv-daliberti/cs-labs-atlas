"""Resolve the William Lee DBLP PID to a named UMass PhD candidate."""

import hashlib
import json

import requests

import atlas_paths as P


def main():
    url = 'https://advancedlearningtech.com/'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    raw = response.content
    assert b'PhD candidates Allison Poh and Will Lee' in raw
    assert b'Artificial Intelligence in Education (AIED 2025)' in raw
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'william-lee-umass-lab.html'
    saved.write_bytes(raw)
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'William Lee'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['Will Lee'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('The DBLP PID gives the William/Will Lee aliases, links ORCID '
                '0009-0003-6049-8082, and lists the same AIED 2025 publication cluster '
                'as the Advanced Learning Technologies Lab. The lab explicitly names '
                'Will Lee as a PhD candidate in 2025. The DBLP VT ISE affiliation '
                'is not a dated VT faculty appointment.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/38/5896-2'], dblp_window=9,
                      affiliation_notes=['University of Massachusetts Amherst',
                                         'Virginia Tech Grado Department of Industrial and Systems Engineering',
                                         'University of Alabama in Huntsville']),
        faculty_evidence=[], status_evidence=[dict(
            url=url, sha256=hashlib.sha256(raw).hexdigest(),
            raw_path=str(saved.relative_to(P.ROOT)), observed='2026-11-10',
            quote=('faculty member Dr. Ivon Arroyo and PhD candidates '
                   'Allison Poh and Will Lee'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment in 2016–2026 is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded William Lee student role')


if __name__ == '__main__':
    main()
