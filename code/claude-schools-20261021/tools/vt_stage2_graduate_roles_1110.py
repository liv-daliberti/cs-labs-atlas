"""Review two VT graduate researchers using saved institutional role pages."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


CASES = (
    ('Salman Ahmed', 'https://news.vt.edu/articles/2022/01/contact-tracing-apps-cybersecurity.html',
     ('Salman Ahmed (left), computer science graduate researcher',),
     'A dated VT news caption identifies him as a CS graduate researcher in 2022.'),
    ('Mohamed W. Hassan', 'https://itass.kaust.edu.sa/topics/high-performance-computing-0',
     ('Mohamed W. Hassan was a Postdoctoral Research Fellow in the Accelerated Connected Computing Lab at KAUST from 2022–2025.',
      'He received his PhD in Electrical and Computer Engineering from Virginia Tech in 2021.'),
     'KAUST records a 2021 VT doctorate followed by a 2022–2025 KAUST postdoctoral role.'),
)


def main():
    path = P.data('cs-related-review.json', 'vt')
    doc = json.loads(path.read_text())
    existing = {x['name'] for x in doc['decisions']}
    candidates = {x['name']: x for x in json.loads(P.data('cs-related-candidates.json', 'vt').read_text())}
    db = W.con('vt')
    added = []
    for name, url, quotes, finding in CASES:
        if name in existing:
            continue
        row = db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (url,)).fetchone()
        assert row and row[0] == 200 and row[2], name
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        text = W.flat(W.extract.blocks(raw, row[3], url))
        assert all(q in text for q in quotes), name
        cand = candidates[name]
        doc['decisions'].append(dict(
            name=name, aliases=cand.get('aliases') or [], source=cand['source'],
            decision='not_faculty_listed',
            reason=finding + ' The reviewed VT 2016–2026 faculty rosters show no professor-rank appointment.',
            cs_basis=cand.get('cs_basis') or {}, faculty_evidence=[],
            status_evidence=[dict(url=url, sha256=row[1], quote=q, observed=row[4][:10]) for q in quotes],
            years_listed=[], units_searched=['VT official faculty rosters 2016–2026'],
            provisional='A later VT faculty appointment requires separate dated evidence.',
        ))
        added.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'reviewed': added}))


if __name__ == '__main__':
    main()
