"""Use a VT-hosted author biography to separate Wei Song's Wuhan role."""

import hashlib
import json
import subprocess

import requests

import atlas_paths as P


def main():
    url = 'https://www.cnsr.ictas.vt.edu/publication/07931708.pdf'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    raw = response.content
    assert raw.startswith(b'%PDF')
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'wei-song-wuhan-bio.pdf'
    saved.write_bytes(raw)
    body = ' '.join(subprocess.check_output(['pdftotext', '-raw', str(saved), '-'], text=True).split())
    assert 'Wei Song is an Associate Professor with the School of Computer Science' in body
    assert 'Wuhan University' in body
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Wei Song'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=[], source='dblp_affiliation', decision='not_faculty_listed',
        reason=('The VT-hosted author biography identifies Wei Song as an associate professor '
                'at Wuhan University, not VT, on the collaborative publication underlying '
                'the VT byline lead. No dated VT professor-rank appointment is established.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/62/1539-6'], dblp_window=25,
                      affiliation_notes=['Wuhan University, Computer School, State Key Laboratory of Software Engineering, China',
                                         'Virginia Polytechnic Institute and State University, Department of Computer Science, Blacksburg, VA, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(), raw_path=str(saved.relative_to(P.ROOT)),
            observed='2026-11-10',
            quote=('Wei Song is an Associate Professor with the School of Computer Science, Wuhan University, China'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT faculty appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Wei Song Wuhan faculty role from VT-hosted paper')


if __name__ == '__main__':
    main()
