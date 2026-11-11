"""Resolve Charles Thornton's doctoral and non-ladder research-rank roles."""

import hashlib
import json

import requests

import atlas_paths as P


def main():
    sources = {
        'lab': 'https://buehrer.ece.vt.edu/Students.html',
        'ece': 'https://ece.vt.edu/people/faculty.html',
        'wireless': 'https://wireless.vt.edu/Directory/faculty.html',
    }
    raw = {}
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    for key, url in sources.items():
        response = requests.get(url, timeout=25)
        response.raise_for_status()
        raw[key] = response.content
        (folder / f'charles-thornton-{key}.html').write_bytes(response.content)
    assert b'Charles Thornton' in raw['lab']
    assert b'Ph.D. Student (2023)' in raw['lab']
    assert b'On the Value of Online Learning for Cognitive Radar Waveform Selection' in raw['lab']
    assert b'Charles Thornton' not in raw['ece']
    assert b'Charles Thornton' not in raw['wireless']

    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Charles E. Thornton'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['Charles Thornton', 'Charlie Thornton', 'Charles Thornton III'],
        source='openalex_rule', decision='research_or_other_rank',
        reason=('Virginia Tech’s Buehrer lab identifies Charles Thornton as its 2023 '
                'ECE PhD student, with the same cognitive-radar thesis/publication '
                'topic as the OpenAlex candidate. His name is absent from the current '
                'official ECE and Wireless faculty listings. Public-payroll indexes '
                'list a later VT Research Assistant Professor title in 2023–2026; '
                'the VT census treats research professor ranks as non-ladder unless '
                'a separate ladder or own-group PI basis is documented. No such basis '
                'is established by these sources.'),
        cs_basis=dict(openalex=['https://openalex.org/A5033205515'],
                      oa_works=30, oa_cs_share=0.533, oa_years=[2019, 2026]),
        faculty_evidence=[dict(
            unit='VT public payroll index',
            url='https://openpayrolls.com/employee/charles-thornton-11134',
            observed='2026-11-10', quote='Research Assistant Professor; 2023–2026',
            ladder=False, source_limit='Secondary index of state payroll; university faculty roster does not list him.')],
        status_evidence=[dict(
            url=sources['lab'], sha256=hashlib.sha256(raw['lab']).hexdigest(),
            raw_path=str((folder / 'charles-thornton-lab.html').relative_to(P.ROOT)),
            observed='2026-11-10',
            quote='Charles Thornton Ph.D. Student (2023) On the Value of Online Learning for Cognitive Radar Waveform Selection')],
        roster_checks=[dict(
            url=sources[key], sha256=hashlib.sha256(raw[key]).hexdigest(),
            raw_path=str((folder / f'charles-thornton-{key}.html').relative_to(P.ROOT)),
            observed='2026-11-10', finding='Name absent from this current faculty list',
            source_limit='An absence cannot prove no appointment.')
            for key in ('ece', 'wireless')],
        years_listed=[], units_searched=['Electrical and Computer Engineering', 'Wireless @ VT'],
        provisional=('Reopen and add to the census if an official VT source establishes '
                     'a ladder professor title or an independently evidenced own-group '
                     'PI basis during 2016–2026.'),
    ))
    doc['counts']['research_or_other_rank'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Charles Thornton research-rank decision')


if __name__ == '__main__':
    main()
