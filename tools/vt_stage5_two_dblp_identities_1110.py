"""Bind two distinctive VT PIs to primary DBLP person records."""

import json
import zlib
from datetime import date

import atlas_paths as P
import school_web as W


ROWS = (
    dict(name='Wu-chun Feng', pid='https://dblp.org/pid/82/6853',
         dblp_name='Wu-chun Feng', orcid='0000-0002-6015-0727',
         school_page='https://website.cs.vt.edu/people/faculty/wu-chun-feng.html',
         school_quote='Wu-chun Feng'),
    dict(name='Steven Flammia', pid='https://dblp.org/pid/73/8658',
         dblp_name='Steven T. Flammia', orcid='0000-0002-3975-0226',
         school_page='https://iac.vt.edu/about/faculty/flammia-steven.html',
         school_quote='Steven Flammia'),
)


def main():
    path = P.data('census-overrides-school.json', 'vt')
    doc = json.loads(path.read_text())
    census = {x['name'] for x in json.loads(P.data('census-faculty.json', 'vt').read_text())['faculty']}
    c = W.con('vt')
    receipts = []
    for item in ROWS:
        name = item['name']
        assert name in census
        page = item['school_page']
        captured = c.execute('select status,sha256,fetched_at,raw_zlib,content_type from live where url=?', (page,)).fetchone()
        assert captured and captured[0] == 200 and captured[1]
        body = W.flat(W.extract.blocks(zlib.decompress(captured[3]), captured[4], page))
        assert item['school_quote'] in body, name
        person = doc.setdefault(name, {})
        assert not person.get('dblp') or person['dblp'] == [item['pid']]
        person['dblp'] = [item['pid']]
        person['why_dblp'] = (
            'Reviewed distinctive DBLP person record with matching name, ORCID and research area; '
            'the separate captured VT faculty page establishes this PI identity. This binds a person, '
            'not papers or an affiliation period.'
        )
        evidence = dict(
            source=item['pid'] + '.html', source_type='DBLP person page',
            source_access='primary page text reviewed through web index; direct DBLP capture returned HTTP 202',
            observed=str(date.today()), dblp_name=item['dblp_name'], orcid=item['orcid'],
            vt_page=page, vt_page_sha256=captured[1], vt_page_captured_at=captured[2],
            vt_page_name=item['school_quote'],
        )
        person['dblp_evidence'] = [evidence]
        receipts.append(dict(name=name, pid=item['pid'], evidence=evidence))
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'bound': [r['name'] for r in receipts]}))


if __name__ == '__main__':
    main()
