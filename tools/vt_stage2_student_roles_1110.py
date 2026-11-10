"""Resolve two byline candidates using captured first-party VT roles."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


ROWS = (
    ('Mark Manuel', 'https://liberalarts.vt.edu/news/articles/2021/09/sister-2-sister-2021.html',
     'Mark Manuel, a graduate researcher in the Virginia Tech Department of Computer Science',
     'not_faculty_listed',
     'Virginia Tech identifies this person as a CS graduate researcher, not a faculty appointment.'),
    ('Ziyang Zhou', 'https://ziyangzhouweb.com/',
     "I'm Ziyang Zhou, a Ph.D. Candidate in Mechanical Engineering at Virginia Tech.",
     'not_faculty_listed',
     'His own research homepage identifies a VT mechanical-engineering PhD candidacy, not a VT faculty appointment.'),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    candidates = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    existing = {x['name'] for x in doc['decisions']}
    db = W.con('vt')
    for name, url, quote, decision, reason in ROWS:
        assert name not in existing, name
        source = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                            (url,)).fetchone()
        assert source and source[0] == 200 and source[2], name
        raw = zlib.decompress(source[2])
        assert hashlib.sha256(raw).hexdigest() == source[1], name
        body = W.flat(W.extract.blocks(raw, source[3], url))
        assert quote in body, name
        candidate = candidates[name]
        doc['decisions'].append(dict(
            name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
            decision=decision, reason=reason,
            cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate.get('dblp_window', 0),
                          affiliation_notes=candidate.get('affiliations') or []),
            faculty_evidence=[], status_evidence=[dict(url=url, sha256=source[1], quote=quote,
                                                      observed=source[4][:10])],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='Reopen if a dated VT professor-rank appointment is found.',
        ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': [x[0] for x in ROWS]}))


if __name__ == '__main__':
    main()
