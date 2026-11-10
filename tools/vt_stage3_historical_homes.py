"""Bind historical VT CS PI homes from the reviewed official CS catalog lines."""

import json

import atlas_paths as P
import census_overrides as CO


def main():
    homes = json.loads(P.data('home-departments-school.json', 'vt').read_text())
    census = {p['name']: p for p in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    catalogs = json.loads((P.CODE / 'hierarchy/vt/reviewed/catalog-listing-sources.json').read_text())['records']
    overrides, save = CO.open_section('vt')
    added = []
    for h in homes:
        if h['status'] != 'hold':
            continue
        person = census[h['name']]
        basis = person['pi_basis']
        assert person['is_pi'] and basis['kind'] == 'ladder_faculty', h['name']
        source = next((r for r in catalogs if r['source_url'] == basis['url']
                       and r['raw_sha256'] == basis['sha256']
                       and basis['quote'] in r['role_lines']), None)
        assert source and source['start_year'] in person['years_listed'], h['name']
        evidence = {k: basis[k] for k in ('url', 'sha256', 'quote')}
        overrides.setdefault(h['name'], {}).update(
            home_department='Computer Science', home_department_evidence=[evidence],
            primary_stated=True,
            why_home_department='Official Virginia Tech Computer Science catalog names this professor under the CS faculty roster; identity resolved in the dated census.')
        added.append(h['name'])
    save()
    print(json.dumps({'reviewed_historical_cs_homes': len(added), 'names': added}))


if __name__ == '__main__':
    main()
