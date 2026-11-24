"""Resolve Carlos Quemada's historical VT role from his university-hosted paper."""

import hashlib
import json
import subprocess

import requests

import atlas_paths as P


def main():
    url = ('https://academica-e.unavarra.es/server/api/core/bitstreams/'
           '6dfbf208-129a-4fd7-9698-e90b4102c362/content')
    response = requests.get(url, timeout=40)
    response.raise_for_status()
    raw = response.content
    assert raw.startswith(b'%PDF')
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'carlos-quemada-mayoral.pdf'
    saved.write_bytes(raw)
    text = subprocess.check_output(['pdftotext', '-layout', str(saved), '-'], text=True)
    normalized = ' '.join(text.split())
    assert 'Carlos Quemada Mayoral' in normalized
    assert 'Virginia Polytechnic Institute' in normalized
    assert 'Post-Doctoral Student' in normalized
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert not any(x['name'] == 'Carlos Quemada' for x in doc['decisions'])
    doc['decisions'].append(dict(
        name='Carlos Quemada', aliases=['Carlos Quemada Mayoral'], source='dblp_affiliation',
        decision='research_or_other_rank',
        reason=('A university-hosted author biography identifies his 2011 Virginia Tech role '
                'as a postdoctoral researcher, before the 2016–2026 census window. No dated '
                'VT professor-rank appointment in the window is established.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/49/8846'], dblp_window=6,
                      affiliation_notes=['Virginia Polytechnic Institute and State University, Blacksurg, VA, USA']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(),
            raw_path=str(saved.relative_to(P.ROOT)), observed='2026-11-10',
            quote=('Carlos Quemada Mayoral; In 2011, he joined the Virginia Polytechnic '
                   'Institute and State University, Blacksburg, VA, USA, as a Post-Doctoral Student'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment in 2016–2026 is found.',
    ))
    doc['counts']['research_or_other_rank'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Carlos Quemada historical VT postdoctoral role')


if __name__ == '__main__':
    main()
