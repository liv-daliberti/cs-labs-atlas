"""Bind two historical VT PI homepages to saved official person pages."""

import hashlib
import html.parser
import json
import zlib
from urllib.parse import urljoin

import atlas_paths as P
import lab_websites as L
import school_web as W


SITES = (
    ('Lenwood S. Heath', 'https://sanghani.cs.vt.edu/people/our-team/faculty/lenwood-heath.html',
     'https://people.cs.vt.edu/~heath/', 'Lenwood S. Heath', 'pi_homepage'),
    ('Layne Watson', 'https://sanghani.cs.vt.edu/people/our-team/faculty/layne-t-watson-2.html',
     'https://people.cs.vt.edu/~ltw/shortvita.html', 'Layne T. Watson', 'pi_homepage'),
    ('Deborah Tatar', 'https://thirdlab.cs.vt.edu/people/deborah-tatar/',
     'https://thirdlab.cs.vt.edu/', 'Deborah Tatar', 'lab_site'),
)


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(v for k, v in attrs if k == 'href' and v)


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    existing = {x['pi'] for x in doc['labs']}
    db = W.con('vt')
    added = []
    for name, source, site, quote, kind in SITES:
        if name in existing:
            continue
        rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
                for u in (source, site)]
        assert all(r and r[0] == 200 and r[2] for r in rows), name
        raw = [zlib.decompress(r[2]) for r in rows]
        assert all(hashlib.sha256(b).hexdigest() == r[1] for b, r in zip(raw, rows)), name
        links = Links()
        links.feed(raw[0].decode('utf-8', 'replace'))
        exact = [urljoin(source, h) for h in links.hrefs
                 if L.normalized_link(urljoin(source, h)) == L.normalized_link(site)]
        assert exact, name
        texts = [W.flat(W.extract.blocks(b, r[3], u)) for b, r, u in zip(raw, rows, (source, site))]
        assert name.split()[-1] in texts[0] and quote in texts[1], name
        assert 'Virginia Tech' in texts[1], name
        at = rows[0][4][:10]
        doc['labs'].append(dict(
            pi=name, url=site, coverage='website', kind=kind,
            reason_code='lab_site' if kind == 'lab_site' else 'pi_homepage_only_no_lab_site',
            found_from=dict(kind='official_page', url=source, sha256=rows[0][1]),
            found_via='school_profile_link', listed_on=source,
            fetched=True, sha256=rows[1][1], names_person=True,
            audited_at=at, checked_at=at,
            checks=[dict(source='school_profile_link', url=site, on=source,
                         result='listed', at=at, source_sha256=rows[0][1], literal_href=exact[0]),
                    dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                         sha256=rows[1][1], quote=quote)],
        ))
        added.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
