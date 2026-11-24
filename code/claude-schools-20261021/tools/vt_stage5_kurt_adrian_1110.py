"""Bind two Virginia Tech PIs to reviewed bibliography person records."""

import json
import zlib
from datetime import date

import atlas_paths as P
import school_web as W


ROWS = (
    dict(name='Kurt Luther', pid='https://dblp.org/pid/33/6201',
         orcid='0000-0003-1809-6269',
         vt_page='https://people.cs.vt.edu/kluther/newlab/kurt-luther.html',
         vt_quote='Dr. Kurt Luther is an associate professor',
         why='DBLP person page and ORCID agree on name and ORCID; the ORCID profile lists Virginia Tech Computer Science employment and a verified vt.edu email domain.'),
    dict(name='Adrian Sandu', pid='https://dblp.org/pid/89/2975',
         orcid=None,
         vt_page='https://people.cs.vt.edu/~asandu/',
         vt_quote='Adrian Sandu Professor of Computer Science',
         why='The distinctive DBLP person bibliography concerns computational science and numerical methods, matching the captured VT professor and Computational Science Laboratory director page. DBLP marks its displayed ORCID as inferred, so that ORCID is not bound.'),
)


def main():
    path = P.data('census-overrides-school.json', 'vt')
    data = json.loads(path.read_text())
    census = {x['name'] for x in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    db = W.con('vt')
    for row in ROWS:
        assert row['name'] in census
        captured = db.execute('select status,sha256,fetched_at,raw_zlib,content_type from live where url=?',
                              (row['vt_page'],)).fetchone()
        assert captured and captured[0] == 200 and captured[1]
        body = W.flat(W.extract.blocks(zlib.decompress(captured[3]), captured[4], row['vt_page']))
        assert row['vt_quote'] in body, row['name']
        person = data.setdefault(row['name'], {})
        assert not person.get('dblp') or person['dblp'] == [row['pid']]
        person['dblp'] = [row['pid']]
        person['why_dblp'] = row['why'] + ' This binds the person only; no papers or affiliation period are admitted.'
        person['dblp_evidence'] = [dict(
            source=row['pid'] + '.html', source_type='DBLP person page',
            source_access='primary page text reviewed through web index; direct DBLP capture unavailable',
            observed=str(date.today()), orcid=row['orcid'],
            vt_page=row['vt_page'], vt_page_sha256=captured[1],
            vt_page_captured_at=captured[2], vt_page_quote=row['vt_quote'],
        )]
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': [r['name'] for r in ROWS]}))


if __name__ == '__main__':
    main()
