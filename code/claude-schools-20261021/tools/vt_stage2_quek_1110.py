"""Resolve Francis Quek's VT-era affiliation from dated university sources."""

import collections
import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


SOURCES = [
    ('https://www.undergradcatalog.registrar.vt.edu/1314/faculty/l-r.html',
     'QUEK, Francis (2004), Prof. of Computer Science.'),
    ('https://stories.tamu.edu/news/2014/12/02/innovation-an-aggie-way-of-life/',
     'Francis Quek, professor of visualization.'),
]


def main():
    review_path = P.CODE / 'hierarchy/vt/reviewed/cs-related-review.json'
    review = json.loads(review_path.read_text())
    if any(x['name'] == 'Francis K. H. Quek' for x in review['decisions']):
        print('already reviewed')
        return
    c = next(x for x in json.loads((P.CODE / 'hierarchy/vt/derived/cs-related-candidates.json').read_text())
             if x['name'] == 'Francis K. H. Quek')
    db = W.con('vt')
    evidence = []
    for url, quote in SOURCES:
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], url
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1]
        assert quote in W.flat(W.extract.blocks(raw, row[3], url))
        evidence.append(dict(url=url, sha256=row[1], quote=quote, observed=row[4][:10]))
    review['decisions'].append(dict(
        name=c['name'], aliases=c.get('aliases') or [], source=c['source'],
        decision='not_faculty_listed',
        reason='Official VT catalog lists Francis Quek as professor in 2013; Texas A&M names him its professor in 2014. The reviewed 2016–2026 VT rosters do not establish a later VT appointment.',
        cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window'),
                      affiliation_notes=c.get('affiliations') or []),
        faculty_evidence=[], status_evidence=evidence,
        years_listed=[], units_searched=['VT CS official 2016–2026 faculty rosters'],
        provisional='Historical VT appointment predates the collection window; review if a later VT appointment is found.'
    ))
    review['counts'] = dict(collections.Counter(x['decision'] for x in review['decisions']))
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(added='Francis K. H. Quek', decisions=len(review['decisions']))))


if __name__ == '__main__':
    main()
