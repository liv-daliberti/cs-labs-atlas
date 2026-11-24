"""Record Uninorte's dated account of Elias Niño's VT degree and return."""

import json
from datetime import date

import atlas_paths as P


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Elias D. Niño'
    assert not any(x['name'] == name for x in doc['decisions'])
    candidate = next(x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())
                     if x['name'] == name)
    url = ('https://www.uninorte.edu.co/web/grupo-prensa/w/'
           'elevar-la-produccion-en-investigacion-objetivo-de-elias-nino-nuevo-director-'
           'del-departamento-de-ingenieria-de-sistemas')
    doc['decisions'].append(dict(
        name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
        decision='not_faculty_listed',
        reason=('The dated Uninorte account identifies a VT doctorate completed in 2015 and '
                'return to full-time Uninorte teaching in early 2016; no VT faculty appointment '
                'in the 2016–2026 window is established.'),
        cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate.get('dblp_window', 0),
                      affiliation_notes=candidate.get('affiliations') or []),
        faculty_evidence=[], status_evidence=[dict(
            url=url, source='Universidad del Norte news, 2018-01-24',
            quote=('finalizó en 2015 un doctorado en la Universidad de Virgnia Tech, '
                   'en Estados Unidos; y se reintegró a Uninorte como docente en el primer período de 2016'),
            observed=str(date.today()),
            access='primary university page reviewed through web index; direct capture blocked by robots',
        )],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT professor-rank appointment is found.',
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(name)


if __name__ == '__main__':
    main()
