"""Resolve Maleq Khan's VT affiliation using a dated university account."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Maleq Khan'
    prior = next((row for row in doc['decisions'] if row['name'] == name), None)
    candidate = next(row for row in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())
                     if row['name'] == name)
    url = ('https://sanghani.cs.vt.edu/news/2018/'
           'dac-urbcomp-actively-participating-kdd-2018-conference-organization-research-presentations.html')
    row = W.con('vt').execute(
        'select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)
    ).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    body = W.flat(W.extract.blocks(raw, row[3], url))
    quote = 'Maleq Khan, assistant professor at Texas A&M University'
    assert quote in body
    own_url = 'https://www.maleqkhan.net/Resume/resume_body.html'
    own_row = W.con('vt').execute(
        'select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (own_url,)
    ).fetchone()
    assert own_row and own_row[0] == 200 and own_row[2]
    own_raw = zlib.decompress(own_row[2])
    assert hashlib.sha256(own_raw).hexdigest() == own_row[1]
    own_text = W.flat(W.extract.blocks(own_raw, own_row[3], own_url))
    own_quote = 'Biocomplexity Institute, Virginia Tech, Blacksburg, VA 24060 Research Scientist, July 2010 - Aug 2016'
    assert own_quote in own_text
    new = dict(
        name=name, aliases=candidate.get('aliases') or [], source=candidate['source'],
        decision='research_or_other_rank',
        reason=('His own CV identifies a VT Biocomplexity Institute research-scientist role ending '
                'August 2016 and a Texas A&M assistant professorship beginning then; a dated VT '
                'professor-rank appointment is not established.'),
        cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate.get('dblp_window', 0),
                      affiliation_notes=candidate.get('affiliations') or []),
        faculty_evidence=[],
        status_evidence=[dict(url=url, sha256=row[1], quote=quote, observed=row[4][:10]),
                         dict(url=own_url, sha256=own_row[1], quote=own_quote,
                              observed=own_row[4][:10])],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='A dated VT faculty appointment would require a separate review.',
    )
    if prior:
        doc['decisions'].remove(prior)
    doc['decisions'].append(new)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(name, new['decision'])


if __name__ == '__main__':
    main()
