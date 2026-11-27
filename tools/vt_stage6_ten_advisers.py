"""Replay ten VT student links from pinned first-party source captures."""

import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / 'hierarchy/vt/reviewed/source-captures'
EVIDENCE = ROOT / 'hierarchy/vt/reviewed/few-students-evidence.json'
SOURCES = {
    'digitaled': ('vt-digitaled-r5.html', '5f8174e19a149fc60396a16063b4cc609a3c3f61a7441eec3a8633afde6cd508', 'https://digitaled.cs.vt.edu/people/'),
    'mughees': ('vt-mughees-r5.html', '5d3e11f4a0f79583f50c3b25c6b935da9b91185d46e4ebdf55bca36bfed49fd0', 'https://sanghani.cs.vt.edu/people/students/mughees-ur-rehman.html'),
    'bert': ('vt-bert-cv-r5.pdf', '9af886bcc7e16351bc9af7aafe268ddf2006fcd07c860349f4975388ee0c8c45', 'https://people.cs.vt.edu/~bhuang/BertHuangCV.pdf'),
    'hci': ('vt-hci-awards-r5.html', '788d642c9b36243d91a5ab3e2b456d8deb0e6b365a911777f64495dadf1ccd42', 'https://hci.icat.vt.edu/news/congratulations-chci-students-and-their-advisors-who-received-vt.html'),
    'highlights': ('vt-highlights-q1-r5.html', '912d78b75d31dd9ff450179ef60ac697d748f316d6f5c287aa4410521a5e0680', 'https://people.cs.vt.edu/ribbens/d/highlights/2024Q1.html'),
    'yusuf': ('vt-yusuf-r5.html', 'f0fbe9fa1b52228712f1469bbabeabc062e83417e4b918cc689573cc0f0812c4', 'https://sanghani.cs.vt.edu/people/students/yusuf-dalva.html'),
    'akshay': ('vt-akshay-r5.html', '48f9fe91172cbc6966aa6ca079d9a43ac5878ce40a09ba476aec936ef10df1de', 'https://news.vt.edu/articles/2025/05/eng-cs-akshay-bansal-first-quantum-phd.html'),
    'ezekiel': ('vt-ezekiel-r5.html', '5a6caf5faea7d67e28d67b071c8cbac4708ead123312fc042ad1b91008968cb4', 'https://people.cs.vt.edu/ecochran/'),
}


def source_text(key):
    filename, sha, _ = SOURCES[key]
    path = SRC_DIR / filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, filename
    if path.suffix == '.pdf':
        text = subprocess.run(['pdftotext', '-layout', str(path), '-'], check=True,
                              capture_output=True, text=True).stdout
    else:
        soup = BeautifulSoup(path.read_bytes(), 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = soup.get_text(' ', strip=True)
    return ' '.join(text.split())


def main():
    pages = {key: source_text(key) for key in SOURCES}
    findings = [
        ('Stephen Edwards', 'Alex Hicks', 'phd', 2026, 'digitaled',
         'Alex Hicks (opens in new tab) PhD CS Education, Help-Seeking Behavior, Office Hours Advisor: Cliff Shaffer & Stephen Edwards', 'advising'),
        ('David H Smith IV.', 'S. Moonwara A. Monisha', 'phd', 2026, 'digitaled',
         'S. Moonwara A. Monisha PhD Databases Education, Automated Grading & Feedback Advisor: David H Smith IV', 'advising'),
        ('Murat Kantarcioglu', 'Mughees Ur Rehman', 'masters', 2026, 'mughees',
         'Mughees Ur Rehman is a master’s degree student in the Department of Computer Science. He is advised by Murat Kantarcioglu.', 'advising'),
        ('Francisco Servant', 'Frank Claytor', 'masters', 2018, 'bert',
         'Frank Claytor. CS MS. Graduated 2018. Advised by Francisco Servant.', 'advising'),
        ('Liqing Zhang', 'Mohammad Shabbir Hasan', 'phd', 2019, 'bert',
         'Mohammad Shabbir Hasan. Graduated 2019. CS PhD. Advised by Liqing Zhang.', 'advising'),
        ('Eugenia Rho', 'Uma Sushmitha Gunturi', 'masters', 2023, 'hci',
         'Uma Sushmitha Gunturi , Master’s student in Computer Science advised by Eugenia Rho', 'advising'),
        ('Huaicheng Li', 'Juinshu Liu', 'student', 2024, 'highlights',
         'Huaicheng Li and his student Juinshu Liu had a paper selected for an IEEE MICRO Top Picks 2024 Honorable Mention award.', 'membership'),
        ('Pinar Yanardag', 'Yusuf Dalva', 'phd', 2026, 'yusuf',
         'Yusuf Dalva is a Ph.D. student in the Department of Computer Science. He is advised by Pinar Yanardag.', 'advising'),
        ('Jamie Sikora', 'Akshay Bansal', 'phd', 2025, 'akshay',
         'Quantum computing Ph.D. graduate Akshay Bansal (from left) and his advisor, Assistant Professor Jamie Sikora', 'advising'),
        ('Atul Mantri', 'Ezekiel Cochran', 'phd', 2026, 'ezekiel',
         'I am a PhD student at Virginia Tech, advised by Atul Mantri', 'advising'),
    ]
    records = json.loads(EVIDENCE.read_text())
    added = []
    for pi, student, role, year, key, quote, relation in findings:
        assert quote in pages[key], (pi, student)
        rec = next((r for r in records if r['pi'] == pi), None)
        if rec is None:
            rec = {'pi': pi, 'students': []}
            records.append(rec)
        if any(s['name'] == student for s in rec['students']):
            continue
        _, sha, url = SOURCES[key]
        rec['students'].append({
            'name': student, 'role': role, 'years': [year, year],
            'years_basis': 'dated degree/news item or current page captured 2026-11-12; no other years inferred',
            'relationship': relation, 'source': 'reviewed_first_party_page',
            'reviewed': True, 'auto': False, 'url': url, 'sha256': sha,
            'quote': quote,
            'note': 'Named first-party VT student link. CV entries report completed VT degrees; current pages are limited to the capture year.',
        })
        added.append((pi, student))
    EVIDENCE.write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
