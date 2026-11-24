"""Review Jian-Xun Wang's dated VT doctorate and later faculty appointments."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Jian-Xun Wang'
    if any(x['name'] == name for x in doc['decisions']):
        print('already reviewed')
        return
    c = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}[name]
    url = 'https://www.duffield.cornell.edu/people/jian-xun-wang/'
    row = W.con('vt').execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    body = W.flat(W.extract.blocks(raw, row[3], url))
    quotes = ('He received his Ph.D. in Aerospace Engineering from Virginia Tech in 2017',
              'before joining Notre Dame as a tenure-track Assistant Professor in 2018.',
              'starting in 2025')
    assert all(q in body for q in quotes)
    doc['decisions'].append(dict(
        name=name, aliases=c.get('aliases') or [], source=c['source'],
        decision='not_faculty_listed',
        reason='Cornell records a VT doctorate in 2017, UC Berkeley postdoctoral training, Notre Dame faculty appointment from 2018, and Cornell appointment in 2025. Reviewed VT 2016–2026 faculty rosters show no VT professor-rank appointment.',
        cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window', 0),
                      affiliation_notes=c.get('affiliations') or []),
        faculty_evidence=[],
        status_evidence=[dict(url=url, sha256=row[1], quote=q, observed=row[4][:10]) for q in quotes],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='A separate VT professor appointment would require dated evidence.',
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': name, 'decision': 'not_faculty_listed'}))


if __name__ == '__main__':
    main()
