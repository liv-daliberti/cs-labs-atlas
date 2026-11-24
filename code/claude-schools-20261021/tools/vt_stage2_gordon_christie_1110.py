"""Resolve Gordon Christie's VT degrees and Johns Hopkins appointment."""

import hashlib
import json
import subprocess

import requests

import atlas_paths as P


def main():
    url = 'https://www.nationalacademies.org/cdn/materials/9fba0ab5-b1c4-42ae-b8e7-eb398327c017'
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    raw = response.content
    assert raw.startswith(b'%PDF')
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'gordon-christie-national-academies.pdf'
    saved.write_bytes(raw)
    body = ' '.join(subprocess.check_output(['pdftotext', '-raw', str(saved), '-'], text=True).split())
    assert 'Gordon Christie' in body and 'Johns Hopkins University Applied Physics' in body
    assert 'Virginia Tech in 2013 and 2016' in body
    assert 'beginning of 2017' in body
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Gordon A. Christie'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['Gordon Christie'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('A National Academies conference biography identifies VT MS and PhD degrees '
                'in 2013 and 2016 and a Johns Hopkins Applied Physics Laboratory research role '
                'beginning in 2017. This explains the VT connection without establishing a '
                'VT professor-rank appointment in the 2016–2026 census window.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/215/3335'], dblp_window=25,
                      affiliation_notes=['Johns Hopkins University, Baltimore, MD, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(), raw_path=str(saved.relative_to(P.ROOT)),
            observed='2026-11-10', quote=('Dr. Gordon Christie is a senior researcher at The Johns '
                'Hopkins University Applied Physics Laboratory, where he has worked since the beginning of 2017. '
                'He received his M.S. and Ph.D. degrees in Computer Engineering from Virginia Tech in 2013 and 2016'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Gordon Christie degree and Johns Hopkins researcher role')


if __name__ == '__main__':
    main()
