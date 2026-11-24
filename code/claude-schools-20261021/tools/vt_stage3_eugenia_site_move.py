"""Document Eugenia Rho's present lab site and its move to Emory."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    if any(row['pi'] == 'Eugenia Rho' for row in doc['labs']):
        return
    urls = ('https://eugeniarho.com/', 'https://eugeniarho.com/sail/')
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone() for url in urls]
    assert all(row and row[0] == 200 and row[2] for row in rows)
    bodies = [zlib.decompress(row[2]) for row in rows]
    assert all(hashlib.sha256(blob).hexdigest() == row[1] for blob, row in zip(bodies, rows))
    texts = [W.flat(W.extract.blocks(blob, row[3], url))
             for blob, row, url in zip(bodies, rows, urls)]
    assert 'Assistant Professor of Computer Science at Emory University' in texts[0]
    assert 'Dr. Eugenia Rho' in texts[1] and 'SAIL' in texts[1]
    at = rows[0][4][:10]
    doc['labs'].append(dict(
        pi='Eugenia Rho', url=urls[1], coverage='reason', kind='other_institution_site',
        reason_code='site_at_other_institution',
        reason=('Her current SAIL lab page identifies her as director; her own homepage now '
                'identifies Emory University as her institution. The historical VT period '
                'remains in the census, but this is not a current VT lab site.'),
        checked_at=at, audited_at=at,
        checks=[dict(source='candidate_site', url=urls[0], result='ok', at=at,
                     sha256=rows[0][1], quote='Assistant Professor of Computer Science at Emory University'),
                dict(source='candidate_site', url=urls[1], result='ok', at=rows[1][4][:10],
                     sha256=rows[1][1], quote='Dr. Eugenia Rho')],
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('Eugenia Rho')


if __name__ == '__main__':
    main()
