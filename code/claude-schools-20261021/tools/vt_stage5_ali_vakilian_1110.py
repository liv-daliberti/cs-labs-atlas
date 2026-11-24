"""Bind historical VT PI Ali Vakilian to the DBLP record on his own site."""

import json
import zlib
from datetime import date

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W


def main():
    url = 'https://www.mit.edu/~vakilian/'
    pid = 'https://dblp.org/pid/116/4679'
    db = W.con('vt')
    row = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[1]
    soup = BeautifulSoup(zlib.decompress(row[3]), 'html.parser')
    body = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'Ali Vakilian' in body
    assert 'Previously: Assistant Professor, CS at Virginia Tech' in body
    assert pid + '.html' in {a.get('href') for a in soup.select('a[href]')}
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    person = data.setdefault('Ali Vakilian', {})
    assert not person.get('dblp') or person['dblp'] == [pid]
    person['dblp'] = [pid]
    person['why_dblp'] = ('The historical VT assistant professor names and links to this DBLP person record from his captured personal university page. This binds a person, not papers or a VT affiliation period.')
    person['dblp_evidence'] = [dict(source=url, source_type='personal university homepage',
                                   source_sha256=row[1], fetched_at=row[2],
                                   quote='Previously: Assistant Professor, CS at Virginia Tech',
                                   self_link=pid + '.html', observed=str(date.today()))]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': 'Ali Vakilian', 'pid': pid}))


if __name__ == '__main__':
    main()
