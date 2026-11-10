"""Review two VT byline candidates against dated primary career accounts."""

import json
from datetime import date

import atlas_paths as P


REVIEWS = {
    'Dong Zhao': dict(
        decision='research_or_other_rank',
        reason=('Michigan State University identifies his VT role as postdoctoral, '
                'then lists him as MSU faculty; no VT professor-rank appointment is established.'),
        evidence=[dict(
            url='https://research.msu.edu/climate/event/campus-convening-climate-change-energy-and-materials',
            quote='Prior to joining MSU, he was a Postdoctoral Fellow at Virginia Tech where he earned his Ph.D.',
            source='MSU Office of Research and Innovation',
            access='primary-page text reviewed through web index; direct institutional capture returned a shell',
        ), dict(
            url='https://www.canr.msu.edu/spdc/uploads/cv/dong%20zhao_cv_spdc_wcag2.0_2018.pdf',
            quote='2014-15 Post-Doctoral Fellow, Virginia Center for Housing Research, Myers-Lawson School of Construction, Virginia Tech',
            source='faculty CV hosted by Michigan State University',
            access='primary PDF text reviewed through web index; direct capture disallowed by robots',
        )],
    ),
    'Chen Wang': dict(
        decision='not_faculty_listed',
        reason=('His 2019 peer-reviewed paper biography identifies a VT electrical-engineering PhD '
                'and a 2019 Dominion Energy appointment; a VT faculty appointment is not established.'),
        evidence=[dict(
            url='https://vtechworks.lib.vt.edu/bitstream/handle/10919/96676/08854186.pdf',
            quote=('He joined the Department of Electric Transmission System Protection, '
                   'Dominion Energy, VA, in 2019.'),
            source='2019 IEEE Access author biography in VT repository',
            access='primary PDF text reviewed through web index; repository direct capture returned 503',
        )],
    ),
}


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    candidates = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    existing = {x['name']: x for x in doc['decisions']}
    for name, review in REVIEWS.items():
        assert name not in existing, name
        candidate = candidates[name]
        doc['decisions'].append(dict(
            name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision=review['decision'], reason=review['reason'],
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate.get('dblp_window', 0),
                          affiliation_notes=candidate.get('affiliations') or []),
            faculty_evidence=[], status_evidence=[dict(x, observed=str(date.today())) for x in review['evidence']],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='Reopen if a dated VT faculty appointment is found.',
        ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': list(REVIEWS)}))


if __name__ == '__main__':
    main()
