"""Record Yufei Blankenship's VT degree and dated industry researcher role."""

import hashlib
import json

import requests

import atlas_paths as P


def main():
    url = ('https://web.ecs.baylor.edu/faculty/dong/elc5396_fall2017/'
           'COMG_20170301_Mar_2017.pdf')
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    raw = response.content
    assert raw.startswith(b'%PDF')
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'yufei-blankenship-ieee-2017.pdf'
    saved.write_bytes(raw)
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Yufei W. Blankenship'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['Yufei Wu', 'Yufei Blankenship'],
        source='dblp_affiliation', decision='not_faculty_listed',
        reason=('The named author biography in a 2017 IEEE Communications Magazine paper '
                'says she earned an electrical engineering PhD from Virginia Tech in 2000, '
                'worked at Motorola Labs from 2000–2007, and was an Ericsson standards '
                'researcher in 2017. The VT relationship is education before the census '
                'window; this source does not support a VT professor-rank role in-window.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/55/1787-3'], dblp_window=17,
                      affiliation_notes=['Research in Motion', 'Motorola', 'Virginia Tech']),
        faculty_evidence=[], status_evidence=[dict(
            url=url, sha256=hashlib.sha256(raw).hexdigest(),
            raw_path=str(saved.relative_to(P.ROOT)), observed='2026-11-10',
            quote=('Yufei Blankenship ... received her Ph.D. degree in electrical '
                   'engineering from Virginia Tech in 2000 ... currently a '
                   'standards researcher with Ericsson.'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment in 2016–2026 is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Yufei Blankenship degree and industry role')


if __name__ == '__main__':
    main()
