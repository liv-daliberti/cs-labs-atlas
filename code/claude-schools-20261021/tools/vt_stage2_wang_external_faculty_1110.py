"""Review two VT-PhD bylines against dated external faculty appointments."""

import hashlib
import json
import zlib
from datetime import date

import atlas_paths as P
import school_web as W


ROWS = (
    dict(name='Shuo Wang', current='https://www.eng.ufl.edu/about/contact/college-directory/name/shuo-wang/',
         current_quote='Education Ph.D., 2005, Virginia Tech',
         earlier='https://news.ece.ufl.edu/wp-content/uploads/sites/15/Legacy/ECENewsFall2014.pdf',
         earlier_quote='ECE Florida will gain two additional faculty members beginning January 2015.',
         reason=('A UF faculty announcement dates his UF appointment to January 2015; the current '
                 'UF profile identifies a 2005 VT doctorate. No VT faculty period in 2016–2026 is established.')),
    dict(name='Xingwei Wang', current='https://www.uml.edu/engineering/electrical-computer/faculty/wang-xingwei.aspx',
         current_quote='Doctor of Philosophy (Ph.D.), Electrical Engineering - Virginia Tech.',
         earlier='https://faculty.uml.edu/xwang/people.html',
         earlier_quote='Then she joined UMass Lowell as an Assistant Professor in 2006.',
         reason=('A historical UML laboratory biography dates her UML faculty appointment to 2006; '
                 'the current UML profile identifies the VT doctorate. No VT faculty period in '
                 '2016–2026 is established.')),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    candidates = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    existing = {x['name'] for x in doc['decisions']}
    db = W.con('vt')
    for item in ROWS:
        name = item['name']
        assert name not in existing
        url = item['current']
        r = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone()
        assert r and r[0] == 200 and r[2]
        raw = zlib.decompress(r[2])
        assert hashlib.sha256(raw).hexdigest() == r[1]
        text = W.flat(W.extract.blocks(raw, r[3], url))
        assert name in text and item['current_quote'] in text
        c = candidates[name]
        doc['decisions'].append(dict(
            name=name, aliases=c.get('aliases') or [], source=c['source'],
            decision='not_faculty_listed', reason=item['reason'],
            cs_basis=dict(dblp=[c['dblp']], dblp_window=c.get('dblp_window', 0),
                          affiliation_notes=c.get('affiliations') or []),
            faculty_evidence=[], status_evidence=[
                dict(url=url, sha256=r[1], quote=item['current_quote'], observed=r[4][:10]),
                dict(url=item['earlier'], quote=item['earlier_quote'], observed=str(date.today()),
                     access='primary university source reviewed through web index; direct capture failed'),
            ],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='Reopen if a dated VT professor-rank appointment is found.',
        ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': [x['name'] for x in ROWS]}))


if __name__ == '__main__':
    main()
