"""Record three individual VT zero-student searches over saved first-party pages."""

import hashlib
import json

from bs4 import BeautifulSoup

import atlas_paths as P


REVIEWS = {
    'Shengwei An': {
        'sources': [
            ('https://answ.in/', 'shengwei-home-20261112.html',
             'a7d9703220c451d3a1212d1031fd2ee2bac635fc6a83be497de126f76ad68fa6',
             'I am actively looking for self-motivated Ph.D. students'),
            ('https://website.cs.vt.edu/people/faculty/shengwei-an.html', 'shengwei-vt-20261112.html',
             'd2045aa6f87bf5978b58cf254d1ed4146891a22730fdf863046e076ebab601a5',
             'Shengwei An'),
        ],
        'why': 'The PI homepage describes a VT appointment, publications, teaching and active PhD recruitment, but has no named lab members or advisees. The linked official CS faculty profile identifies the PI and research area but supplies no member list. No student is inferred from publication coauthors; revisit when a roster or explicit adviser record is found.',
    },
    'Steven Flammia': {
        'sources': [
            ('https://sflammia.github.io/', 'steven-home-20261112.html',
             '75408ea370dea48ee069d424ae4678ffa4c8d3564a8319eeb630297c62aa6e47',
             'Professor, Virginia Tech, Department of Computer Science'),
            ('https://iac.vt.edu/about/faculty/flammia-steven.html', 'steven-vt-20261112.html',
             '8f4218e08b94cf5cae884e8d29b39609abc3c95bcf4e9b5a569c2c3892791cae',
             'Steven Flammia is the director of the Center for Quantum Architecture'),
        ],
        'why': 'His PI homepage identifies his VT professorship and lists research and publications without a student or group roster. The Institute for Advanced Computing profile describes his center leadership and team-building role, but names no student members. The center faculty team is not treated as his lab students; revisit if a named student roster appears.',
    },
    'Peng Gao': {
        'sources': [
            ('https://people.cs.vt.edu/penggao/', 'peng-home-20261112.html',
             '4054ff534d2b7d10ce63c81f7a14fe27b5e2fb3fae5757a703f8cd6b882a18d2',
             'Prospective students: I am looking for strong and motivated postdocs'),
            ('https://website.cs.vt.edu/people/faculty/peng-gao.html', 'peng-vt-20261112.html',
             '72af2f17d91d1849d72f6a652882549831d5c25a2091bdb942e0261cbe4a999e',
             'Peng Gao'),
        ],
        'why': 'The PI-owned CS page covers biography, publications, teaching, service and open positions; its student text recruits prospective applicants and names no current or former student. The official VT CS profile also has no member or advisee list. Recruitment text and publication coauthors are not evidence of a PI–student relation.',
    },
}


def main():
    path = P.data_w('lab-coverage-reasons.json', 'vt')
    reasons = json.loads(path.read_text()) if path.exists() else {}
    capture_dir = P.WORK / 'hierarchy/vt/reviewed/source-captures'
    for pi, review in REVIEWS.items():
        checked = []
        for url, filename, sha, marker in review['sources']:
            raw = (capture_dir / filename).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sha
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            visible = ' '.join(soup.get_text(' ', strip=True).split())
            assert marker in visible, (pi, marker)
            checked.append(f'{url} (sha256 {sha}, captured 2026-11-12): {filename}')
        reasons.setdefault(pi, {})['students'] = dict(
            code='sources_exhausted', why=review['why'], sources_checked=checked,
            by='codex-vt-stage6-r3-1112', on='2026-11-12',
        )
    path.write_text(json.dumps(reasons, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(reasoned=list(REVIEWS))))


if __name__ == '__main__':
    main()
