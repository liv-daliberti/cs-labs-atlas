"""Anchor three VT faculty identities with exact first-party title or role evidence."""

import hashlib
import json

import requests

import atlas_paths as P


PAGES = {
    'Atul Mantri': ('https://www.atulmantri.com/cv/',
                    'Lattice-Based Quantum Advantage from Rotated Measurements'),
    'Jamie Sikora': ('https://www.quics.umd.edu/people/jamie-sikora',
                     'Cheat-Penalised Quantum Weak Coin-Flipping'),
}


def save(folder, label, url, headers=None):
    response = requests.get(url, headers=headers or {}, timeout=30)
    response.raise_for_status()
    raw = response.content
    path = folder / label
    path.write_bytes(raw)
    return dict(url=url, raw_path=str(path.relative_to(P.ROOT)),
                sha256=hashlib.sha256(raw).hexdigest(), observed='2026-11-10'), raw


def main():
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/stage5-final'
    folder.mkdir(parents=True, exist_ok=True)
    overrides_path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(overrides_path.read_text())
    audit = json.loads((P.CODE / 'hierarchy/vt/reviewed/stage5-exact-dblp-audit.json').read_text())['people']
    pubs = json.loads((P.CODE / 'hierarchy/vt/reviewed/stage5-exact-dblp-pubs.json').read_text())['people']
    for name, (url, title) in PAGES.items():
        evidence, raw = save(folder, name.lower().replace(' ', '-') + '.html', url)
        text = raw.decode('utf-8', 'replace')
        assert name in text and title in text and 'Virginia Tech' in text
        assert len(audit[name]) == 1 and not audit[name][0]['disambiguation']
        person = audit[name][0]
        assert title in {work['title'].rstrip('.') for work in pubs[name]['titles']}
        entry = overrides.setdefault(name, {})
        assert not entry.get('dblp') or entry['dblp'] == [person['pid']]
        entry['dblp'] = [person['pid']]
        entry['why_dblp'] = ('Unique exact-name DBLP person in the local September 2026 snapshot shares an exact '
                             'publication title with a captured first-party page naming the professor and Virginia Tech. '
                             'This binds the identity, not every DBLP paper.')
        entry['dblp_evidence'] = [dict(source='dblp-2026-09-01.xml.gz',
                                       person_record_sha256=person['person_record_sha256'],
                                       pid=person['pid'], matching_title=title, page=evidence)]
    name = 'David H Smith IV.'
    oid = '0000-0002-6572-4347'
    url = f'https://pub.orcid.org/v3.0/{oid}/record'
    evidence, raw = save(folder, 'david-h-smith-orcid.json', url, {'Accept': 'application/json'})
    record = json.loads(raw)
    assert record['person']['name']['credit-name']['value'] == 'David H Smith IV'
    jobs = [item['employment-summary'] for group in
            record['activities-summary']['employments']['affiliation-group']
            for item in group['summaries']]
    assert any(job['organization']['name'] == 'Virginia Tech' and
               job['role-title'] == 'Assistant Professor' for job in jobs)
    entry = overrides.setdefault(name, {})
    assert not entry.get('orcid') or entry['orcid'] == [f'https://orcid.org/{oid}']
    entry['orcid'] = [f'https://orcid.org/{oid}']
    entry['why_orcid'] = ('The ORCID record gives the exact full-name credit and a Virginia Tech Assistant Professor '
                           'employment. This anchors the person; it does not admit all ORCID works.')
    entry['orcid_evidence'] = [dict(identifier=oid, credit_name='David H Smith IV',
                                    employment='Virginia Tech: Assistant Professor', source=evidence)]
    overrides_path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': list(PAGES) + [name]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
