"""Review two VT-byline people with captured first-party appointment histories."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


ROWS = (
    ('Lei Li', 'https://leicuhk.github.io/teaching/',
     'I was a Teaching Assistant for “ECE4614: Telecomm. Networks” from Jan. 2019 to May. 2019.',
     'not_faculty_listed',
     'His first-party teaching history identifies a 2019 VT ECE teaching-assistant role; it does not support a VT faculty appointment.'),
    ('Jong-Hwan Kim', 'https://sejong.elsevierpure.com/en/persons/jong-hwan-kim/',
     '2014 Ph.D., Virginia Tech',
     'not_faculty_listed',
     'His university profile records a VT PhD in 2014 and a Korea Military Academy professorship throughout 2015–2026, with no VT faculty appointment.'),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    cands = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    existing = {x['name'] for x in doc['decisions']}
    db = W.con('vt')
    for name, url, quote, decision, reason in ROWS:
        assert name not in existing, name
        r = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone()
        assert r and r[0] == 200 and r[2], name
        raw = zlib.decompress(r[2])
        assert hashlib.sha256(raw).hexdigest() == r[1]
        text = W.flat(W.extract.blocks(raw, r[3], url))
        assert quote in text
        if name == 'Jong-Hwan Kim':
            assert '(2015-2026) Professor in Korea Military Academy' in text
        c = cands[name]
        doc['decisions'].append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'], decision=decision,
            reason=reason,
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window', 0),
                          affiliation_notes=c.get('affiliations') or []),
            faculty_evidence=[], status_evidence=[dict(url=url, sha256=r[1], quote=quote,
                                                      observed=r[4][:10])],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='Reopen if a dated VT professor-rank appointment is found.',
        ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': [x[0] for x in ROWS]}))


if __name__ == '__main__':
    main()
