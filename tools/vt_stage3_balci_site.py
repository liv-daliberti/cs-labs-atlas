"""Verify Osman Balci's lab homepage from the saved VT faculty profile."""

import hashlib
import html.parser
import json
import zlib
from urllib.parse import urljoin

import atlas_paths as P
import lab_websites as L
import school_web as W


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
    name = 'Osman Balci'
    if any(x['pi'] == name for x in doc['labs']):
        print('already reviewed')
        return
    source = 'https://website.cs.vt.edu/people/faculty/osman-balci.html'
    site = 'https://manta.cs.vt.edu/balci/'
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
            for u in (source, site)]
    assert all(r and r[0] == 200 and r[2] for r in rows)
    raw = [zlib.decompress(r[2]) for r in rows]
    assert all(hashlib.sha256(b).hexdigest() == r[1] for b, r in zip(raw, rows))
    links = Links()
    links.feed(raw[0].decode('utf-8', 'replace'))
    exact = [urljoin(source, h) for h in links.hrefs
             if L.normalized_link(urljoin(source, h)) == L.normalized_link(site)]
    assert exact
    body = W.flat(W.extract.blocks(raw[1], rows[1][3], site))
    assert all(q in body for q in ('OSMAN BALCI', 'Learning Transformation Research Group', 'Virginia Tech'))
    at = rows[0][4][:10]
    doc['labs'].append(dict(
        pi=name, url=site, coverage='website', kind='lab_site', reason_code='lab_site',
        found_from=dict(kind='official_page', url=source, sha256=rows[0][1]),
        found_via='school_profile_link', listed_on=source,
        fetched=True, sha256=rows[1][1], names_person=True,
        audited_at=at, checked_at=at,
        checks=[dict(source='school_profile_link', url=site, on=source,
                     result='listed', at=at, source_sha256=rows[0][1], literal_href=exact[0]),
                dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                     sha256=rows[1][1], quote='OSMAN BALCI')],
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'pi': name, 'site': site}))


if __name__ == '__main__':
    main()
