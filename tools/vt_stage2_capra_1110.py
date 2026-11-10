"""Review Robert G. Capra's VT connection from a dated university bio."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Robert G. Capra'
    if any(x['name'] == name for x in doc['decisions']):
        print('already reviewed')
        return
    cand = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}[name]
    url = 'https://ischool.utexas.edu/events/colloquim-rob-capra-unc-chapel-hill-situated-information-seeking-user-perspectives-tasks'
    row = W.con('vt').execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    body = W.flat(W.extract.blocks(raw, row[3], url))
    quotes = ('Robert Capra is a Professor in the School of Information and Library Science at the University of North Carolina at Chapel Hill.',
              'He holds a Ph.D. in computer science from Virginia Tech')
    assert all(q in body for q in quotes)
    doc['decisions'].append(dict(
        name=name, aliases=cand.get('aliases') or [], source=cand['source'],
        decision='not_faculty_listed',
        reason='A dated university biography identifies the VT connection as a computer-science doctorate and his 2022 professorship at UNC; reviewed VT 2016–2026 faculty rosters show no professor-rank appointment.',
        cs_basis=cand.get('cs_basis') or {}, faculty_evidence=[],
        status_evidence=[dict(url=url, sha256=row[1], quote=q, observed=row[4][:10]) for q in quotes],
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='A later VT professor appointment would require separate dated evidence.',
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': name, 'decision': 'not_faculty_listed'}))


if __name__ == '__main__':
    main()
