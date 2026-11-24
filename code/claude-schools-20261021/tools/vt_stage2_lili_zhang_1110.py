"""Resolve Lili Zhang's VT visit as pre-window and Hohai professorship."""

import hashlib
import json

import requests

import atlas_paths as P


def main():
    oid = '0000-0001-9429-8378'
    url = f'https://pub.orcid.org/v3.0/{oid}/record'
    response = requests.get(url, headers={'Accept': 'application/json'}, timeout=20)
    response.raise_for_status()
    raw = response.content
    record = json.loads(raw)
    assert record['person']['name']['given-names']['value'] == 'Lili'
    assert record['person']['name']['family-name']['value'] == 'Zhang'
    jobs = [x['employment-summary'] for group in
            record['activities-summary']['employments']['affiliation-group']
            for x in group['summaries']]
    assert any(x['organization']['name'] == 'Hohai University' and
               x['role-title'] == 'Associate Professor' for x in jobs)
    folder = P.ROOT / 'scratch/vt-followthrough-1110/stage2-role-sources'
    folder.mkdir(parents=True, exist_ok=True)
    saved = folder / 'lili-zhang-orcid.json'
    saved.write_bytes(raw)
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Lili Zhang'
    assert not any(x['name'] == name for x in doc['decisions'])
    doc['decisions'].append(dict(
        name=name, aliases=['Zhang Lili'], source='dblp_affiliation',
        decision='not_faculty_listed',
        reason=('The candidate DBLP PID links this ORCID and dates its Virginia Tech ECE '
                'affiliation to 2011–2012, before the 2016–2026 census window. The public '
                'ORCID employment identifies an associate professorship at Hohai University. '
                'The VT connection does not establish a VT professor-rank role in-window.'),
        cs_basis=dict(dblp=['https://dblp.org/pid/00/6528-2'], dblp_window=14,
                      affiliation_notes=['Hohai University, College of Computer and Information Engineering, Nanjing, China',
                                         'Virginia Tech, Department of Electrical and Computer Engineering (2011–2012)']),
        faculty_evidence=[], status_evidence=[dict(url=url,
            sha256=hashlib.sha256(raw).hexdigest(), raw_path=str(saved.relative_to(P.ROOT)),
            observed='2026-11-10', quote='Lili Zhang; Hohai University; Associate Professor')],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment in 2016–2026 is found.',
    ))
    doc['counts']['not_faculty_listed'] += 1
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('recorded Lili Zhang pre-window VT affiliation and Hohai role')


if __name__ == '__main__':
    main()
