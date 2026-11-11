"""Resolve Mostafa Taha's VT doctorate against his Carleton faculty profile."""

import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    url = 'https://experts.carleton.ca/mostafa-taha'
    r = W.con('vt').execute('select status,sha256,raw_zlib,content_type from live where url=?',
                            (url,)).fetchone()
    assert r and r[0] == 200
    text = W.flat(W.extract.blocks(zlib.decompress(r[2]), r[3], url))
    assert 'Taha holds a Ph.D. degree from the Secure Embedded Systems Lab' in text
    assert 'Virginia Tech (VT)' in text and 'Carleton University' in text
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert not any(x['name'] == 'Mostafa M. I. Taha' for x in doc['decisions'])
    doc['decisions'].append(dict(
        name='Mostafa M. I. Taha', aliases=['Mostafa Taha'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('Carleton identifies this security researcher as its professor and names '
                'his VT Computer Engineering doctorate. The VT affiliation is a doctoral '
                'research link; no dated 2016–2026 VT professor-rank appointment is '
                'established by this source.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/33/3884'], dblp_window=7,
                      affiliation_notes=['Carleton University, Ottawa, ON, Canada',
                                         'Virginia Tech, Blacksburg, Virginia, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url, sha256=r[1],
            observed='2026-11-10',
            quote=('Professor Faculty of Engineering and Design; Taha holds a Ph.D. '
                   'degree from the Secure Embedded Systems Lab in the Computer '
                   'Engineering Department of Virginia Tech (VT).'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Mostafa Taha Carleton faculty / VT doctorate evidence')


if __name__ == '__main__':
    main()
