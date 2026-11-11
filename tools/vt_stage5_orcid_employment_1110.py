"""Bind first-party ORCID identities that name the PI and Virginia Tech employment."""

import hashlib
import json
import requests

import atlas_paths as P


PEOPLE = {
    'Alexey Onufriev': '0000-0002-4930-6612',
    'Brendan David-John': '0000-0003-3292-1130',
    'Debswapna Bhattacharya': '0000-0002-9630-0141',
    'Kirshanthan Sundararajah': '0000-0001-6384-062X',
    'Jiaming Cui': '0000-0002-2685-2776',
    'Jin-Hee Cho': '0000-0002-5908-4662',
    'Matthew Hicks': '0000-0002-3639-4342',
    'Muhammad Ali Gulzar': '0000-0002-8007-8662',
    'Shengwei An': '0000-0003-0564-0018',
    'Thang Hoang': '0000-0003-2229-3863',
    'Tu Vu': '0009-0009-5241-1972',
    'Xuan Wang': '0000-0002-1381-8958',
}


def main():
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/orcid'
    folder.mkdir(parents=True, exist_ok=True)
    result = []
    for name, oid in PEOPLE.items():
        url = f'https://pub.orcid.org/v3.0/{oid}/record'
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=20)
        response.raise_for_status()
        raw = response.content
        data = json.loads(raw)
        n = data['person']['name']
        printed = ' '.join((n['given-names']['value'], n['family-name']['value']))
        assert printed == name, (name, printed)
        jobs = [x['employment-summary'] for group in
                data['activities-summary']['employments']['affiliation-group']
                for x in group['summaries']]
        vt = [job for job in jobs if job['organization']['name'] == 'Virginia Tech']
        assert len(vt) == 1, name
        if name != 'Shengwei An':
            assert 'professor' in (vt[0]['role-title'] or '').lower(), name
        raw_path = folder / f'{oid}.json'
        raw_path.write_bytes(raw)
        item = overrides.setdefault(name, {})
        assert not item.get('orcid') or item['orcid'] == [f'https://orcid.org/{oid}']
        item['orcid'] = [f'https://orcid.org/{oid}']
        item['why_orcid'] = ('First-party public ORCID record names the exact PI and a Virginia Tech employment entry. The school appointment and periods are checked separately; the ORCID anchor does not admit any papers.')
        item['orcid_evidence'] = [dict(url=url, raw_path=str(raw_path.relative_to(P.ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(), observed='2026-11-10',
            person_name=printed, organization='Virginia Tech',
            role_title=vt[0]['role-title'], start_date=vt[0]['start-date'],
            source='ORCID public record; self-asserted employment')]
        result.append(name)
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': result}))


if __name__ == '__main__':
    main()
