"""Bind four multiply named ORCID search results using exact institution roles."""

import hashlib
import json
import zlib

import requests

import atlas_paths as P
import school_web as W


PEOPLE = {
    'Dimitrios Nikolopoulos': ('0000-0003-0217-8307', 'Virginia Polytechnic Institute and State University', None),
    'Jiaqi Leng': ('0000-0002-9276-2832', 'Virginia Polytechnic Institute and State University', None),
    'Sanmay Das': ('0000-0002-6814-871X', 'Virginia Tech', None),
    'Lifu Huang': ('0000-0002-2743-7718', 'University of California, Davis',
                   'https://wilburone.github.io/index.html'),
}


def main():
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/orcid'
    folder.mkdir(parents=True, exist_ok=True)
    db = W.con('vt')
    bound = []
    for name, (oid, institution, personal_url) in PEOPLE.items():
        url = f'https://pub.orcid.org/v3.0/{oid}/record'
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=20)
        response.raise_for_status()
        raw = response.content
        data = json.loads(raw)
        person = data['person']['name']
        assert person['given-names']['value'] + ' ' + person['family-name']['value'] == name
        jobs = [x['employment-summary'] for group in
                data['activities-summary']['employments']['affiliation-group']
                for x in group['summaries']]
        matched = [job for job in jobs if job['organization']['name'] == institution]
        assert len(matched) == 1 and 'professor' in (matched[0]['role-title'] or '').lower()
        personal = None
        if personal_url:
            row = db.execute('select status,sha256,raw_zlib from live where url=?',
                             (personal_url,)).fetchone()
            assert row and row[0] == 200
            body = zlib.decompress(row[2]).decode('utf-8', 'replace')
            assert name in body and 'Virginia Tech' in body and 'UC Davis' in body
            personal = dict(url=personal_url, sha256=row[1])
        raw_path = folder / f'{oid}.json'
        raw_path.write_bytes(raw)
        entry = overrides.setdefault(name, {})
        assert not entry.get('orcid') or entry['orcid'] == [f'https://orcid.org/{oid}']
        entry['orcid'] = [f'https://orcid.org/{oid}']
        entry['why_orcid'] = ('The exact-name ORCID record has a professor-rank employment at the institution documented for this PI. Other same-name search results lacked this role. The VT period is reviewed separately; no papers are admitted by this anchor.')
        entry['orcid_evidence'] = [dict(url=url, raw_path=str(raw_path.relative_to(P.ROOT)),
            sha256=hashlib.sha256(raw).hexdigest(), observed='2026-11-10',
            person_name=name, institution=institution,
            role_title=matched[0]['role-title'], corroborating_personal_site=personal)]
        bound.append(name)
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': bound}))


if __name__ == '__main__':
    main()
