"""Replay six VT student/adviser findings from pinned first-party captures."""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / 'hierarchy/vt/reviewed/source-captures'
EVIDENCE = ROOT / 'hierarchy/vt/reviewed/few-students-evidence.json'

SOURCES = {
    'dac': ('vt-dac-graduates-2020-r4.html', '2ba0238c20a35ea305d6e7d433db8359c7ee70e3939f6797ea357eb419b76bba',
            'https://sanghani.cs.vt.edu/news/2020/congratulations-dacs-spring-summer-graduates.html'),
    'gautam': ('vt-aakash-gautam-r4.html', '9d5f0d8d13fc43e410a1e7b52d6621f05dbd753bbe02893e45dac71ffcb20035',
               'https://hci.icat.vt.edu/news/aakash-gautam-wins-outstanding-dissertation-award-at-sigchi-2022.html'),
    'keith': ('vt-brian-keith-r4.html', 'e89ee8df903b3598aebadfa246a87b24e0071072c18b26a8246d4fa45d99158c',
             'https://sanghani.cs.vt.edu/people/students/brian-keith.html'),
    'sanmay': ('vt-sanmay-lab-r4.html', 'b81d04d331cc6a9642acad67ef4699cc5cbd9e905518f0fd6ee587a7a4e0d2ff',
              'https://people.cs.vt.edu/sanmay/lab.html'),
    'farabi': ('vt-shafkat-farabi-r4.html', 'c4e4575085f08812d63ed59b8321a035b7ba16810bfa9464e2933766a0530a19',
              'https://farabi-shafkat.github.io/'),
    'tmvs': ('vt-tmvs-alumni-r4.html', '9d87a5caeadb3064ad9a6db6f380544c5b14e433bc9069c64ce82a0a3822497a',
             'https://tmvs.me.vt.edu/people/Alumni.html'),
}


def visible(key):
    filename, sha, _ = SOURCES[key]
    raw = (CAPTURES / filename).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha, filename
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return ' '.join(soup.get_text(' ', strip=True).split())


def main():
    pages = {key: visible(key) for key in SOURCES}
    findings = [
        ('B. Aditya Prakash', 'Bijaya Adhikari', 2020, 'dac',
         'Bijaya Adhikari , advised by B. Aditya Prakash, is receiving a Ph.D. in computer science.', None),
        ('Layne Watson', 'Tyler Chang', 2020, 'dac',
         'Tyler Chang , advised by Layne Watson, is receiving a Ph.D. in computer science.', None),
        ('Layne Watson', 'Thomas Lux', 2020, 'dac',
         'Thomas Lux , advised by Layne Watson, will complete his Ph.D. in computer science.', None),
        ('Deborah Tatar', 'Aakash Gautam', 2022, 'gautam',
         'He was advised by Deborah Tatar',
         'Gautam graduated from Virginia Tech with a PhD in Computer Science and Applications this year.'),
        ('Tanushree Mitra', 'Brian Keith', 2023, 'keith',
         'Brian Keith was a Ph.D. student in the Department of Computer Science. He was co-advised by Chris North and Tanushree Mitra.', None),
        ('Sanmay Das', 'Shafkat Farabi', 2026, 'farabi',
         "Currently, I am pursuing my PhD at Virginia Tech's Institute for Advanced Computing under the supervision of Dr. Sanmay Das", None),
        ('Adrian Sandu', 'Ekansh Chaturvedi', 2025, 'tmvs',
         'Ekansh Chaturvedi , April 03, 2025 Dissertation: " Non-smooth dynamics and sensitivity analysis of joints with clearances in differential variational inequality framework " - Co-advised by Dr. Adrian Sandu',
         None),
    ]
    assert 'Current Ph.D. Students and Postdocs Gaurab Pokharel Shafkat Farabi' in pages['sanmay']
    records = json.loads(EVIDENCE.read_text())
    added = []
    for pi, student, year, key, quote, second in findings:
        assert quote in pages[key], (pi, student, quote)
        if second:
            assert second in pages[key], (pi, student, second)
        rec = next((r for r in records if r['pi'] == pi), None)
        if rec is None:
            rec = {'pi': pi, 'students': []}
            records.append(rec)
        old = next((s for s in rec['students'] if s['name'] == student), None)
        _, sha, url = SOURCES[key]
        row = {
            'name': student, 'role': 'phd', 'years': [year, year],
            'years_basis': 'dated first-party VT graduate/adviser page; captured 2026-11-12',
            'relationship': 'advising', 'source': 'official_student_profile',
            'reviewed': True, 'auto': False, 'url': url, 'sha256': sha,
            'quote': quote,
            'note': 'Explicit VT adviser relation; no other appointment years inferred.',
        }
        if pi == 'Sanmay Das':
            row['group_url'] = SOURCES['sanmay'][2]
            row['group_sha256'] = SOURCES['sanmay'][1]
            row['note'] = 'PI-owned current lab roster plus student-owned statement of VT PhD and Sanmay Das supervision.'
        if old is None:
            rec['students'].append(row)
            added.append((pi, student))
        else:
            old.update(row)
    EVIDENCE.write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
