"""Bind three VT faculty to exact full-name DBLP people with primary sources."""

import hashlib
import json

import requests

import atlas_paths as P


PEOPLE = {
    'R. Benjamin Knapp': dict(pid='70/2357', person_sha='f29b8c37dc1d15c648d33418dc04f2e94f8097e5b6657e69703f7005297c5abb',
        url='https://news.vt.edu/articles/2026/01/eng-cs-knapp-conferred-emeritus-status.html',
        name='R. Benjamin Knapp', marker='Virginia Tech'),
    'Cal Ribbens': dict(pid='30/4586', person_sha='9951cc3643c157fa077debfd92c3aae2387c066db4973f97f42b57ce3f9b7c63',
        url='https://people.cs.vt.edu/ribbens/r/publications.html',
        name='Calvin J. Ribbens', marker='Combining performance and priority for scheduling resizable parallel applications'),
    'Scott McCrickard': dict(pid='23/1491', person_sha='e36e0c2139bfe7f7a5c644d17a3da3eebdebac232e6884740044411ade4e9231',
        url='https://people.cs.vt.edu/~mccricks/',
        name='D. Scott McCrickard', marker='Virginia Tech'),
}


def main():
    folder = P.ROOT / 'scratch/vt-followthrough-1110/identity-sources/stage5-variants'
    folder.mkdir(parents=True, exist_ok=True)
    path = P.data('census-overrides-school.json', 'vt')
    overrides = json.loads(path.read_text())
    for name, info in PEOPLE.items():
        response = requests.get(info['url'], timeout=30)
        response.raise_for_status()
        raw = response.content
        body = raw.decode('utf-8', 'replace')
        assert info['name'].lower() in body.lower() and info['marker'].lower() in body.lower(), name
        saved = folder / (name.lower().replace(' ', '-').replace('.', '') + '.html')
        saved.write_bytes(raw)
        pid = 'https://dblp.org/pid/' + info['pid']
        entry = overrides.setdefault(name, {})
        assert not entry.get('dblp') or entry['dblp'] == [pid]
        entry['dblp'] = [pid]
        if name == 'Cal Ribbens':
            why = ('VT first-party publication page names Calvin J. Ribbens and lists a distinctive publication '
                   'also attributed to the exact full-name DBLP person. The second short-name DBLP PID is not imported.')
        elif name == 'Scott McCrickard':
            why = ('Reviewed VT alias joins Scott to D. Scott McCrickard; the DBLP person uses that exact full name, '
                   'lists Virginia Tech affiliation, and links to his own VT homepage. No blanket paper admission.')
        else:
            why = ('VT news names R. Benjamin Knapp as its professor and ICAT director; the DBLP person has the '
                   'same distinctive full name and a da Vinci’s Cube paper tied to the same VT project. This '
                   'anchors the person, not all works.')
        entry['why_dblp'] = why
        entry['dblp_evidence'] = [dict(source='dblp-2026-09-01.xml.gz', pid=pid,
                                       person_record_sha256=info['person_sha'],
                                       first_party_url=info['url'],
                                       first_party_raw_path=str(saved.relative_to(P.ROOT)),
                                       first_party_sha256=hashlib.sha256(raw).hexdigest(),
                                       first_party_quote=info['name'], observed='2026-11-10')]
    path.write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': list(PEOPLE)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
