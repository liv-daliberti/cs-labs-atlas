"""Resolve two VT-affiliated DBLP candidates with institutional role accounts."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


ROLES = (
    ('Wentao Ma', 'https://aeroelasticity.pratt.duke.edu/people/wentao-ma',
     'Wentao is currently pursuing his PhD at the Multiphysics Modeling and Computation (M2C) Lab at Virginia Tech',
     'Duke identifies him as a PhD student in VT\'s Multiphysics Modeling and Computation lab.'),
    ('Alex McCaskey',
     'https://www.ornl.gov/news/advanced-software-framework-expedites-quantum-classical-programming/',
     'Alex McCaskey, a computer scientist at ORNL who has been developing and refining the framework since 2016',
     'ORNL identifies him as an ORNL computer scientist in a dated 2020 account, with work there since 2016.'),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    existing = {row['name'] for row in doc['decisions']}
    candidates = {row['name']: row for row in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    db = W.con('vt')
    added = []
    for name, url, quote, role in ROLES:
        if name in existing:
            continue
        candidate = candidates[name]
        assert candidate['source'] == 'dblp_affiliation'
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                         (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        text = W.flat(W.extract.blocks(raw, row[3], url))
        assert quote in text, name
        doc['decisions'].append(dict(
            name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision='not_faculty_listed',
            reason=role + ' Reviewed VT faculty rosters do not establish a later VT professor appointment.',
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate.get('dblp_window', 0),
                          affiliation_notes=candidate.get('affiliations') or []),
            faculty_evidence=[],
            status_evidence=[dict(url=url, sha256=row[1], quote=quote, observed=row[4][:10])],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='A separate dated VT professor appointment would reopen this decision.',
        ))
        added.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
