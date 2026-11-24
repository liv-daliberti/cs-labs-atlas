"""Bind historical VT PI Dongyoon Lee to identifiers linked from his own site."""

import json
import zlib
from datetime import date

from bs4 import BeautifulSoup

import atlas_paths as P
import school_web as W


def main():
    url = 'https://www3.cs.stonybrook.edu/~dongyoon/'
    pid = 'https://dblp.org/pid/90/4053'
    db = W.con('vt')
    row = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?', (url,)).fetchone()
    assert row and row[0] == 200 and row[1]
    html = zlib.decompress(row[3])
    soup = BeautifulSoup(html, 'html.parser')
    body = ' '.join(soup.get_text(' ', strip=True).split())
    assert 'Dongyoon Lee' in body
    assert 'Before joining Stony Brook University, I worked as an assistant professor at Virginia Tech (2014-2019)' in body
    links = {a.get('href') for a in soup.select('a[href]')}
    assert pid + '.html' in links
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    person = data.setdefault('Dongyoon Lee', {})
    assert not person.get('dblp') or person['dblp'] == [pid]
    person['dblp'] = [pid]
    person['why_dblp'] = ('The historical VT professor names and links to his DBLP person record from his own captured current university page. This binds a person, not papers or a VT affiliation period.')
    person['dblp_evidence'] = [dict(source=url, source_type='personal university homepage',
                                   source_sha256=row[1], fetched_at=row[2],
                                   quote='Before joining Stony Brook University, I worked as an assistant professor at Virginia Tech (2014-2019)',
                                   self_link=pid + '.html', observed=str(date.today()))]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': 'Dongyoon Lee', 'pid': pid}))


if __name__ == '__main__':
    main()
