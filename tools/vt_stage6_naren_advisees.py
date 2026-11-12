"""Add dated graduates explicitly named as Naren Ramakrishnan's advisees."""

import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

import atlas_paths as P


URL = 'https://people.cs.vt.edu/naren/bio.html'
SHA = '671c31805097e74b45746f797dad7c76f2cafce6f5c0ae2c3db36f29b2faa638'
CAPTURE = Path('/n/fs/resemble/homogenizing-science/code/scratch/vt-stage6-1112/naren-bio.html')


def main():
    raw = CAPTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    soup = BeautifulSoup(raw, 'html.parser')
    visible = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'As an advior, Naren is proud of his students and their careers:' in visible
    assert 'Naren Ramakrishnan is the Thomas L. Phillips Professor of Engineering at Virginia Tech' in visible
    records = json.loads(P.data_w('few-students-evidence.json', 'vt').read_text())
    rec = next(r for r in records if r['pi'] == 'Naren Ramakrishnan')
    existing = {r['name'] for r in rec['students']}
    added = []
    html = raw.decode('utf-8')
    phd_html, masters_html = html.split('<B>MS (Thesis) graduates</B>', 1)
    for section, block in [('phd', phd_html.split('<B>PhD graduates</B>', 1)[1]), ('masters', masters_html)]:
      for item in re.findall(r'<li>([^<\n]+)', block, flags=re.I):
        quote = ' '.join(BeautifulSoup(item, 'html.parser').get_text(' ', strip=True).split())
        match = re.fullmatch(r'(\d{4}): (.+?)(?: \(with .+?\))?', quote)
        if not match:
            # A pre-2016 entry has a trailing employer; no admitted row needs it.
            assert quote.startswith('2014: Sathappan Muthiah, eBay'), quote
            continue
        year, name = int(match.group(1)), match.group(2)
        if year < 2016 or name in existing:
            continue
        assert quote in visible
        rec['students'].append(dict(
            name=name, role=section, years=[year, year], years_basis='dated graduation on PI-owned VT advisee list',
            relationship='advising', source='pi_owned_advisee_list', reviewed=True, auto=False,
            url=URL, sha256=SHA, quote=quote,
            note='PI explicitly identifies these as his students; the graduation year establishes the endpoint only.',
        ))
        added.append(name)
    P.data_w('few-students-evidence.json', 'vt').write_text(json.dumps(records, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(added=len(added), names=added)))


if __name__ == '__main__':
    main()
