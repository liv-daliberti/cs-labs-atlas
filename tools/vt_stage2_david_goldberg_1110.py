"""Resolve the David Goldberg VT-affiliation lead with SDSU appointment evidence."""

import collections
import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


PROFILE = 'https://business.sdsu.edu/directory/dgoldberg'
GRANT = 'https://business.sdsu.edu/news/2021/01/fowler-professors-secure-grant-to-predict-and-prevent-us-navy-equipment-failures'


def captured(db, url, quotes):
    row = db.execute('select status,sha256,fetched_at,raw_zlib,content_type from live where url=?',
                     (url,)).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[3])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    text = W.flat(W.extract.blocks(raw, row[4], url))
    assert all(quote in text for quote in quotes)
    return row


def main():
    db = W.con('vt')
    profile = captured(db, PROFILE, ('David Goldberg is a Professor of Management Information Systems',
                                    "doctoral and bachelor's degrees from Virginia Tech"))
    grant = captured(db, GRANT, ('principal investigator David Goldberg', 'text-mining model'))
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    assert 'David Goldberg' not in {x['name'] for x in doc['decisions']}
    candidate = next(x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())
                     if x['name'] == 'David Goldberg')
    assert candidate['dblp'] == 'https://dblp.org/pid/228/2382'
    doc['decisions'].append(dict(
        name='David Goldberg', aliases=candidate.get('aliases') or [], source=candidate['source'],
        decision='not_faculty_listed',
        reason='SDSU identifies this text-mining researcher as its MIS professor, explicitly identifying Virginia Tech as his degree institution. The 2021 SDSU PI grant corroborates the appointment during the study window; the VT-linked coauthor/byline does not establish a VT faculty role.',
        cs_basis=dict(dblp=[candidate['dblp']], dblp_window=candidate['dblp_window'],
                      affiliation_notes=candidate.get('affiliations') or []),
        faculty_evidence=[], status_evidence=[
            dict(url=PROFILE, sha256=profile[1], observed=profile[2][:10],
                 quote="David Goldberg is a Professor of Management Information Systems ... He received his doctoral and bachelor's degrees from Virginia Tech."),
            dict(url=GRANT, sha256=grant[1], observed=grant[2][:10],
                 quote='principal investigator David Goldberg'),
        ], years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='Reopen if a dated VT faculty appointment or another same-name DBLP identity is found.',
    ))
    doc['counts'] = dict(collections.Counter(x['decision'] for x in doc['decisions']))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': 'David Goldberg'}))


if __name__ == '__main__':
    main()
