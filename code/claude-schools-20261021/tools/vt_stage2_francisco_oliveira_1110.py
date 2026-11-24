"""Resolve Francisco Oliveira's VT-degree affiliation against UECE's roster."""

import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    url = 'https://www.uece.br/ppgcc/instituicional/corpo-docente/'
    row = W.con('vt').execute('select status,sha256,raw_zlib,content_type from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200
    quote = 'Francisco Carlos de Mattos Brito Oliveira Doutorado, Virginia Tech, EUA.'
    text = W.flat(W.extract.blocks(zlib.decompress(row[2]), row[3], url))
    assert quote in ' '.join(text.split())
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert not any(x['name'] == 'Francisco C. M. B. Oliveira' for x in doc['decisions'])
    doc['decisions'].append(dict(
        name='Francisco C. M. B. Oliveira',
        aliases=['Francisco Carlos de Mattos Brito Oliveira'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('The current official UECE computer-science faculty roster names the full '
                'person and lists Virginia Tech as his doctorate institution. This explains '
                'the VT connection; it does not establish a VT professor-rank appointment '
                'during 2016–2026.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/151/4184'], dblp_window=33,
                      affiliation_notes=['State University of Ceará, Fortaleza, Brazil',
                                         'Virginia Tech, Blacksburg, VA, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url, sha256=row[1],
            observed='2026-11-10',
            quote=('Corpo Docente; Membros Permanentes; Francisco Carlos de Mattos '
                   'Brito Oliveira; Doutorado, Virginia Tech, EUA.; Engenharia De '
                   'Software E Interface Homem-Máquina'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Francisco Oliveira UECE faculty and VT degree evidence')


if __name__ == '__main__':
    main()
