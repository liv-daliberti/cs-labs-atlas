"""Bind historical VT PIs to DBLP IDs linked by their captured personal sites."""

import json
import zlib
from datetime import date

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W


ROWS = (
    ('B. Aditya Prakash', 'https://faculty.cc.gatech.edu/~badityap/',
     'https://dblp.org/pid/06/3956',
     'B. Aditya Prakash Professor and Associate Chair for Academic Affairs'),
)


def main():
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    census = {x['name'] for x in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    db = W.con('vt')
    for name, url, pid, quote in ROWS:
        assert name in census
        row = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?',
                         (url,)).fetchone()
        assert row and row[0] == 200 and row[1]
        soup = BeautifulSoup(zlib.decompress(row[3]), 'html.parser')
        body = ' '.join(soup.get_text(' ', strip=True).split())
        assert quote in body, name
        assert pid + '.html' in {a.get('href') for a in soup.select('a[href]')}, name
        person = data.setdefault(name, {})
        assert not person.get('dblp') or person['dblp'] == [pid]
        person['dblp'] = [pid]
        person['why_dblp'] = ('A captured current personal faculty site names this historical VT PI and directly links the DBLP person record. The VT appointment is supported separately by the dated census. This binds a person, not papers.')
        person['dblp_evidence'] = [dict(source=url, source_type='personal university homepage',
                                       source_sha256=row[1], fetched_at=row[2], quote=quote,
                                       self_link=pid + '.html', observed=str(date.today()))]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': [x[0] for x in ROWS]}))


if __name__ == '__main__':
    main()
