"""Review Mohammed Baidas's VT doctorate against his Kuwait faculty record."""

import hashlib
import json
import subprocess
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Mohammed W. Baidas'
    if any(x['name'] == name for x in doc['decisions']):
        print('already reviewed')
        return
    cand = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}[name]
    vt = 'https://ece.vt.edu/content/dam/ece_vt_edu/research/annual-report/pdf/2013_AR.pdf'
    ku = 'https://pure.ku.edu.kw/en/persons/mohammed-w-h-baidas/'
    db = W.con('vt')
    ev = []
    for url in (vt, ku):
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2]
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1]
        if url == vt:
            body = subprocess.run(['pdftotext', '-layout', '-', '-'], input=raw,
                                  capture_output=True, check=True).stdout.decode('utf-8', 'replace')
            quotes = ('Baidas, Mohammed W.', 'Node Selection, Synchronization and Power Al-')
            assert '2012' in body and all(q in body for q in quotes)
        else:
            body = W.flat(W.extract.blocks(raw, row[3], url))
            quotes = ('Mohammed W H Baidas Professor Professor, Electrical Engineering',)
            assert all(q in body for q in quotes)
        ev.extend(dict(url=url, sha256=row[1], quote=q, observed=row[4][:10]) for q in quotes)
    doc['decisions'].append(dict(
        name=name, aliases=cand.get('aliases') or [], source=cand['source'],
        decision='not_faculty_listed',
        reason='VT ECE lists his 2012 doctorate; Kuwait University lists him as its electrical-engineering professor. Reviewed VT 2016–2026 rosters show no later professor-rank appointment.',
        cs_basis=dict(dblp=[cand['dblp']], dblp_window=cand.get('dblp_window', 0),
                      affiliation_notes=cand.get('affiliations') or []),
        faculty_evidence=[], status_evidence=ev,
        years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
        provisional='A later VT professor appointment requires separate dated evidence.',
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': name, 'decision': 'not_faculty_listed'}))


if __name__ == '__main__':
    main()
