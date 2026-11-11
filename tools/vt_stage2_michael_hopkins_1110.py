"""Record the dated VT doctoral role for robotics author Michael A. Hopkins."""

import hashlib
import json

import atlas_paths as P


def main():
    raw = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/michael-hopkins-dissertation.pdf'
    sha = '80dc6468e124a8e55092f5cc87c17f2e831d187efdf37cd6cf127a3076a62a86'
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == sha
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert not any(x['name'] == 'Michael A. Hopkins' for x in doc['decisions'])
    doc['decisions'].append(dict(
        name='Michael A. Hopkins', aliases=[], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('The original VT dissertation names Michael A. Hopkins as a 2014 Computer '
                'Engineering doctoral candidate with the same robotics coauthors and topic '
                'as the candidate DBLP person. It establishes a dated student role, not a '
                '2016–2026 VT professor-rank appointment.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/117/3271'], dblp_window=9,
                      affiliation_notes=['Virginia Tech, Blacksburg, VA, USA'],
                      identity_overlap=['Alexander Leonessa', 'Dennis W. Hong',
                                        'humanoid locomotion and whole-body control']),
        faculty_evidence=[], status_evidence=[dict(
            url='https://vtechworks.lib.vt.edu/server/api/core/bitstreams/a12f1d5b-49b1-4352-8fee-7c09d6e6ed85/content',
            raw_path=str(raw.relative_to(P.ROOT)), sha256=sha, observed='2026-11-10',
            quote=('Michael A. Hopkins; Dissertation submitted to the Faculty of the '
                   'Virginia Polytechnic Institute and State University in partial '
                   'fulfillment of the requirements for the degree of Doctor of '
                   'Philosophy in Computer Engineering; 8 December 2014; '
                   'Alexander Leonessa, Co-chair; Dennis W. Hong'))],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated 2016–2026 VT professor-rank appointment is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Michael A. Hopkins doctoral role')


if __name__ == '__main__':
    main()
