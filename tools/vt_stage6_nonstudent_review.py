"""Review clear nonstudents and ambiguous roster entries on VT lab pages."""

import hashlib
import json
import sqlite3
import zlib

from bs4 import BeautifulSoup

import atlas_paths as P


NOT_PEOPLE = {
    'NSF Review Panels', 'Virginia Tech', 'U.S. Senate Presentations',
    'Personal Webpage', 'Commonwealth Cyber Initiative',
    'LLM Hallucination Characterization', "Jakob Nielsen UX Tigers' Cover",
    'On-demand Programming Assistance', 'Robert Bosch RTC',
}
UNCLEAR = {'Sanjana Ghanta', 'Uzair Shiekh', 'Yicheng Ren', 'Alex Levy'}
CITATION_ONLY = {'Vishal Patel'}
SERVICE_ONLY = {'Yubin Xia'}


def main():
    additions = json.loads(P.data('labpage-additions.json', 'vt').read_text())['students']
    source = P.data('labpage-audit-captures.sqlite', 'vt')
    db = sqlite3.connect(f'file:{source}?mode=ro', uri=True)
    path = P.data_w('student-decisions.json', 'vt')
    decisions = json.loads(path.read_text()) if path.exists() else {}
    reviewed = 0
    for row in additions:
        name = row['name']
        if row.get('role') != 'postdoc' and name not in NOT_PEOPLE | UNCLEAR | CITATION_ONLY | SERVICE_ONLY:
            continue
        capture = db.execute('select content from captures where sha256=? and status=200 limit 1',
                             (row['sha256'],)).fetchone()
        assert capture, (row['pi'], name)
        content = zlib.decompress(capture[0])
        assert hashlib.sha256(content).hexdigest() == row['sha256']
        visible = ' '.join(BeautifulSoup(content, 'html.parser').get_text(' ', strip=True).split())
        assert ' '.join(row['quote'].split()) in visible
        unclear = name in UNCLEAR
        why = ('The name appears as a program committee co-chair, not in the lab member roster.'
               if name in SERVICE_ONLY else
               'The name appears in a publication citation, not in the lab member roster.'
               if name in CITATION_ONLY else
               'The Student Researchers section gives no individual VT affiliation, degree, or dated status; hold for a second source.'
               if unclear else
               'The page labels this person a postdoc, which is outside the student relation rule.'
               if row.get('role') == 'postdoc' else
               'The named entry is a title, organization, page link, or employer, not a person in this PI lab.')
        pi_decisions = decisions.setdefault(row['pi'], {})
        assert name not in pi_decisions or pi_decisions[name]['decision'] in ('not', 'unclear')
        pi_decisions[name] = dict(decision='unclear' if unclear else 'not', why=why,
                                  url=row.get('capture_url') or row['url'], sha256=row['sha256'],
                                  quote=row['quote'], observed='2026-11-10', role_was=row.get('role'))
        reviewed += 1
    assert sum(len(items) for items in decisions.values()) == 20
    path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(excluded=reviewed, pis=len(decisions))))


if __name__ == '__main__':
    main()
