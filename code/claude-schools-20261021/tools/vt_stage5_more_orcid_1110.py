"""Add ORCID anchors with exact person plus institution or verified VT email."""

import hashlib
import json
import zlib

import requests

import atlas_paths as P
import school_web as W


PEOPLE = {
    'Aisling Kelliher': ('0000-0001-9175-2176', 'University of Southern California',
                        'https://cinema.usc.edu/faculty/profile.cfm?id=62323'),
    'Alla Rozovskaya': ('0009-0002-6001-6752', 'City University of New York',
                       'https://www.cs.qc.cuny.edu/rozovskaya.html'),
    'Bimal Viswanath': ('0000-0002-6559-9689', 'Virginia Tech', None),
    'Eric Pauley': ('0000-0002-2197-9137', 'verified-vt-email', None),
    'Eugenia Rho': ('0000-0002-0961-4397', 'Virginia Tech', None),
    'Hoda Eldardiry': ('0000-0002-9712-6667', 'Virginia Tech', None),
    'Palash Sashittal': ('0000-0001-6581-4839', 'Virginia Tech', None),
    'Sumeet Khatri': ('0000-0002-9858-0511', 'Virginia Tech', None),
}


def main():
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/orcid'
    folder.mkdir(parents=True, exist_ok=True)
    site_db = W.con('vt')
    names = []
    for name, (oid, organization, corroboration_url) in PEOPLE.items():
        url = f'https://pub.orcid.org/v3.0/{oid}/record'
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=20)
        response.raise_for_status()
        raw = response.content
        data = json.loads(raw)
        given = data['person']['name']['given-names']['value']
        family = data['person']['name']['family-name']['value']
        assert f'{given} {family}' == name
        jobs = [x['employment-summary'] for group in
                data['activities-summary']['employments']['affiliation-group']
                for x in group['summaries']]
        if organization == 'verified-vt-email':
            emails = data['person']['emails']['email']
            assert any(x.get('verified') and x['email'].endswith('@vt.edu') for x in emails)
            detail = 'verified vt.edu email on ORCID public record'
        else:
            matches = [x for x in jobs if x['organization']['name'] == organization]
            assert matches, (name, organization)
            detail = f'ORCID employment: {organization}; {matches[0]["role-title"]}'
        corroboration = None
        if corroboration_url:
            row = site_db.execute('select status,sha256,raw_zlib from live where url=?',
                                  (corroboration_url,)).fetchone()
            assert row and row[0] == 200 and name.split()[-1] in zlib.decompress(row[2]).decode('utf-8', 'replace')
            corroboration = dict(url=corroboration_url, sha256=row[1],
                                 institution=organization)
        raw_path = folder / f'{oid}.json'
        raw_path.write_bytes(raw)
        item = overrides.setdefault(name, {})
        assert not item.get('orcid') or item['orcid'] == [f'https://orcid.org/{oid}']
        item['orcid'] = [f'https://orcid.org/{oid}']
        item['why_orcid'] = ('First-party public ORCID record names the exact PI and a corroborating institution or verified VT email. The dated VT PI role is established separately; this anchor does not admit papers.')
        item['orcid_evidence'] = [dict(url=url, raw_path=str(raw_path.relative_to(P.ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(), observed='2026-11-10',
            person_name=name, identity_detail=detail,
            corroborating_current_site=corroboration)]
        names.append(name)
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': names}))


if __name__ == '__main__':
    main()
