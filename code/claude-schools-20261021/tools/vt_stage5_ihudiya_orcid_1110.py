"""Bind Ihudiya Finda Williams to her pen-name ORCID with her VT site."""

import hashlib
import json

import requests

import atlas_paths as P


NAME = 'Ihudiya Finda Williams'
OID = '0000-0002-2531-4634'
SITE = 'https://people.cs.vt.edu/iogburu/?p=46'
CV = 'https://people.cs.vt.edu/iogburu/doc/IFO_Full_CV.pdf'
ORCID = f'https://pub.orcid.org/v3.0/{OID}/record'


def main():
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/ihudiya'
    folder.mkdir(parents=True, exist_ok=True)
    sources = {}
    for label, url, suffix in [('site', SITE, 'html'), ('cv', CV, 'pdf'),
                               ('orcid', ORCID, 'json')]:
        response = requests.get(url, headers={'Accept': 'application/json'} if label == 'orcid' else {}, timeout=30)
        response.raise_for_status()
        raw = response.content
        raw_path = folder / f'{label}.{suffix}'
        raw_path.write_bytes(raw)
        sources[label] = dict(url=url, raw_path=str(raw_path.relative_to(P.ROOT)),
                              sha256=hashlib.sha256(raw).hexdigest(), observed='2026-11-10')
    site = (folder / 'site.html').read_text()
    assert NAME in site and 'Virginia Tech' in site
    assert 'Ihudiya Finda Ogbonnaya-Ogburu' in site and 'pen name' in site
    cv = (folder / 'cv.pdf').read_bytes()
    assert cv.startswith(b'%PDF')
    record = json.loads((folder / 'orcid.json').read_text())
    person = record['person']['name']
    assert person['credit-name']['value'] == 'Ihudiya Finda Ogbonnaya-Ogburu'
    jobs = [item['employment-summary']['organization']['name']
            for group in record['activities-summary']['employments']['affiliation-group']
            for item in group['summaries']]
    assert 'Virginia Tech' in jobs
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    entry = overrides[NAME]
    assert not entry.get('orcid') or entry['orcid'] == [f'https://orcid.org/{OID}']
    entry['orcid'] = [f'https://orcid.org/{OID}']
    entry['why_orcid'] = ('Her Virginia Tech site gives the full school name and explicitly names her publication pen name. '
                          'That exact pen name is the ORCID credit name and the record lists Virginia Tech employment. '
                          'The VT CV corroborates her publication name; this binds the person, not every paper.')
    entry['orcid_evidence'] = [dict(identifier=OID, credit_name=person['credit-name']['value'],
                                    employment='Virginia Tech', sources=sources)]
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'name': NAME, 'orcid': OID, 'sources': sources}, ensure_ascii=False))


if __name__ == '__main__':
    main()
