"""Review Anders Eklund's dated VT role from his current university profile."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Anders Eklund'
    if any(x['name'] == name for x in doc['decisions']):
        print('already reviewed')
        return
    cand = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}[name]
    url = 'https://liu.se/en/employee/andek67'
    row = W.con('vt').execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    page = W.flat(W.extract.blocks(raw, row[3], url))
    quotes = ('Anders Eklund Professor', '2012-2014 Postdoc, Virginia Tech',
              '2021 Associate Professor', '2026 Professor')
    assert all(q in page for q in quotes)
    doc['decisions'].append(dict(
        name=name, aliases=cand.get('aliases') or [], source=cand['source'],
        decision='not_faculty_listed',
        reason='His university CV dates the Virginia Tech role to a postdoc ending in 2014 and later appointments to Linköping; reviewed VT 2016–2026 rosters show no professor-rank appointment.',
        cs_basis=cand.get('cs_basis') or {}, faculty_evidence=[],
        status_evidence=[dict(url=url, sha256=row[1], quote=q, observed=row[4][:10]) for q in quotes],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='A later VT professor appointment would require separate dated evidence.',
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': name, 'decision': 'not_faculty_listed'}))


if __name__ == '__main__':
    main()
