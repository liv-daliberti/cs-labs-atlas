"""Resolve three former VT affiliates from dated university appointment records."""

import collections
import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W
from vt_stage2_student_batch_1110 import text_of


RULES = {
    'Eihab M. Abdel-Rahman': (
        'https://uwaterloo.ca/nano-micro-systems-lab/profiles/professor-eihab-abdel-rahman',
        ['Research Associate, June 1997–December 2005',
         'Assistant Professor, December 2005–June 2011',
         'Associate Professor, July 2011–present'],
        'Waterloo records a VT research-associate appointment ending in 2005 and Waterloo faculty appointments throughout the 2016–2026 window.'),
    'J. Cole Smith': (
        'https://www.clemson.edu/provost/leadership/meet-provost-smith.html',
        ['He earned his Ph.D. in industrial and systems engineering from Virginia Tech',
         '2014 – 2019', 'Earlier in his career, Smith was a professor'],
        'Clemson identifies the VT connection as a doctorate and dates later faculty appointments outside VT.'),
    'Deepak Mathaikutty': (
        'https://ece.vt.edu/content/dam/ece_vt_edu/research/annual-report/pdf/2009_AR.pdf',
        ['2007 PH.D. DEGREES 2008 AWARDED', 'Mathaikutty, Deepak',
         'Metamodeling Driven IP Reuse'],
        'VT ECE lists Deepak Mathaikutty among 2007–08 doctoral degree recipients; no VT professor appointment appears in the reviewed window.'),
}


def main():
    f = P.CODE / 'hierarchy/vt/reviewed/cs-related-review.json'
    doc = json.loads(f.read_text())
    decisions = {d['name']: d for d in doc['decisions']}
    candidates = {c['name']: c for c in json.loads((P.CODE / 'hierarchy/vt/derived/cs-related-candidates.json').read_text())}
    db = W.con('vt')
    added = []
    for name, (url, anchors, reason) in RULES.items():
        if name in decisions:
            continue
        c = candidates[name]
        assert c['source'] == 'dblp_affiliation', name
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        body = text_of(raw, row[3], url)
        assert all(a in body for a in anchors), name
        decisions[name] = dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'],
            decision='not_faculty_listed',
            reason=reason + ' The reviewed VT 2016–2026 faculty rosters show no later professor role.',
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window'),
                          affiliation_notes=c.get('affiliations') or []),
            faculty_evidence=[],
            status_evidence=[dict(url=url, sha256=row[1], quote=a, observed=row[4][:10]) for a in anchors],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='A later VT faculty appointment requires separate dated professor-rank evidence.',
        )
        added.append(name)
    doc['decisions'] = list(decisions.values())
    doc['counts'] = dict(collections.Counter(x['decision'] for x in doc['decisions']))
    f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added, 'remaining': len(candidates)-len(decisions)}))


if __name__ == '__main__':
    main()
