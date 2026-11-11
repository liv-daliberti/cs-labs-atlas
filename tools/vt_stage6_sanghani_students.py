"""Admit VT student–adviser pairs stated on saved Sanghani student profiles.

The source is a current 2026 directory. It establishes only a 2026 relation,
not the student's start date, publication authorship, or exclusive adviser.
"""

import collections
import hashlib
from html.parser import HTMLParser
import json
import urllib.robotparser

import requests
from bs4 import BeautifulSoup

import atlas_paths as P


ADVISERS = {
    'Aadyant Khatri': ['Chang-Tien Lu'],
    'Abhilash Neog': ['Anuj Karpatne'],
    'Adheesh Juvekar': ['Edward Fox'],
    'Ahmed Abdelhady': ['Hoda Eldardiry'],
    'Alexander Kedrowitsch': ['Daphne Yao'],
    'Ali Asgarov': ['Chris Thomas'],
    'Amartya Dutta': ['Anuj Karpatne', 'T. M. Murali'],
    'Amr Aboelnaga': ['Hoda Eldardiry'],
    'Aneesh Jain': ['Ismini Lourentzou'],
    'Aravind Cheruvu': ['Daphne Yao'],
    'Ayush Roy': ['Doug Bowman', 'Chris North'],
    'Barry Menglong Yao': ['Lifu Huang'],
}
HOLDS = {
    'Ahmad Al-Tawaha': 'Ming Jin is not in the current reviewed 93-PI census',
    'Ann Mariya Sunil': 'Manish Bansal is not in the current reviewed 93-PI census',
    'Bhargav Vasireddy': 'Sara Hooshangi is not in the current reviewed 93-PI census',
    'Bilgehan Sel': 'Ming Jin is not in the current reviewed 93-PI census',
}


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def visible(body):
    parser = Text()
    parser.feed(body.decode('utf-8', 'replace'))
    return ' '.join(' '.join(parser.parts).split())


def main():
    source_path = P.WORK / 'hierarchy/vt/reviewed/sanghani-visible-student-advisers.json'
    rows = json.loads(source_path.read_text())['rows']
    assert len(rows) == len(ADVISERS) + len(HOLDS) == 16
    assert {r['name_as_source'] for r in rows} == set(ADVISERS) | set(HOLDS)
    pis = {p['pi']: p for p in json.loads(P.data('pis.json', 'vt').read_text())}
    assert all(pi in pis for names in ADVISERS.values() for pi in names)
    assert all(any(z.get('year') == 2026 for z in pis[pi]['listings']) or
               any(z.get('end') is None and int(z.get('start', '9999')) <= 2026 for z in pis[pi]['periods'])
               for names in ADVISERS.values() for pi in names)

    session = requests.Session()
    robots_url = 'https://sanghani.cs.vt.edu/robots.txt'
    rp = urllib.robotparser.RobotFileParser()
    robots = session.get(robots_url, timeout=25)
    robots.raise_for_status()
    rp.parse(robots.text.splitlines())
    assert rp.can_fetch('GPTBot', rows[0]['profile_url'])
    directory_url, directory_hash = rows[0]['directory_url'], rows[0]['directory_sha256']
    directory = session.get(directory_url, timeout=25)
    directory.raise_for_status()
    assert hashlib.sha256(directory.content).hexdigest() == directory_hash
    cards = BeautifulSoup(directory.content, 'html.parser').select('span.vt-c-card-title a[href]')
    visible_profiles = {a.get('href') for a in cards}
    assert len(visible_profiles) == 16
    assert {r['profile_url'] for r in rows} == visible_profiles

    capture_dir = P.ROOT / 'scratch/vt-followthrough-1110/stage6-sanghani-sources'
    capture_dir.mkdir(parents=True, exist_ok=True)
    (capture_dir / 'student-directory.html').write_bytes(directory.content)
    evidence = collections.defaultdict(list)
    holds = []
    for row in rows:
        name, url = row['name_as_source'], row['profile_url']
        assert rp.can_fetch('GPTBot', url)
        response = session.get(url, timeout=25)
        response.raise_for_status()
        sha = hashlib.sha256(response.content).hexdigest()
        assert sha == row['profile_sha256'], f'changed profile: {name}'
        quote = row['role_and_adviser_quote']
        assert ' '.join(quote.split()) in visible(response.content), f'quote absent: {name}'
        (capture_dir / (url.rsplit('/', 1)[-1])).write_bytes(response.content)
        if name in HOLDS:
            holds.append(dict(student=name, url=url, sha256=sha, quote=quote, reason=HOLDS[name]))
            continue
        role = ('undergraduate' if 'undergraduate student' in quote else
                'masters' if "master's degree student" in quote else 'phd')
        assert role != 'phd' or ('Ph.D.' in quote or 'PhD' in quote)
        for pi in ADVISERS[name]:
            evidence[pi].append(dict(
                name=name, role=role, years=[2026], years_basis='current profile and directory captured 2026-11-10',
                relationship='advising', source='official_student_profile', reviewed=True, auto=False,
                url=url, capture_url=url, sha256=sha, quote=quote,
                directory_url=directory_url, directory_sha256=directory_hash,
                note='Explicit adviser statement; no earlier start date or paper link inferred.',
            ))
    path = P.data_w('few-students-evidence.json', 'vt')
    path.write_text(json.dumps([dict(pi=pi, students=items) for pi, items in sorted(evidence.items())],
                               indent=2, ensure_ascii=False) + '\n')
    hold_path = P.WORK / 'hierarchy/vt/reviewed/sanghani-student-holds.json'
    hold_path.write_text(json.dumps(holds, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(students=len(ADVISERS), lab_student_pairs=sum(map(len, evidence.values())),
                          pis=len(evidence), held=len(holds))))


if __name__ == '__main__':
    main()
