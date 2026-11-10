"""Verify Edward Fox's homepage from his VT-hosted CV."""

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
            self.hrefs.extend(value for key, value in attrs if key == 'href' and value)


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    name = 'Edward Fox'
    if any(row['pi'] == name for row in doc['labs']):
        return
    source = 'https://fox.cs.vt.edu/cv.htm'
    site = 'https://fox.cs.vt.edu/'
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone() for url in (source, site)]
    assert all(row and row[0] == 200 and row[2] for row in rows)
    raw = [zlib.decompress(row[2]) for row in rows]
    assert all(hashlib.sha256(blob).hexdigest() == row[1] for blob, row in zip(raw, rows))
    links = Links()
    links.feed(raw[0].decode('utf-8', 'replace'))
    exact = [urljoin(source, href) for href in links.hrefs
             if L.normalized_link(urljoin(source, href)) == L.normalized_link(site)]
    assert exact
    source_text, site_text = [W.flat(W.extract.blocks(blob, row[3], url))
                              for blob, row, url in zip(raw, rows, (source, site))]
    assert 'EDWARD A. FOX' in source_text and 'Edward A. Fox' in site_text
    at = rows[0][4][:10]
    doc['labs'].append(dict(
        pi=name, url=site, coverage='website', kind='pi_homepage',
        reason_code='pi_homepage_only_no_lab_site',
        found_from=dict(kind='official_page', url=source, sha256=rows[0][1]),
        found_via='school_profile_link', listed_on=source,
        fetched=True, sha256=rows[1][1], names_person=True,
        audited_at=at, checked_at=at,
        checks=[dict(source='school_profile_link', url=site, on=source,
                     result='listed', at=at, source_sha256=rows[0][1], literal_href=exact[0]),
                dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                     sha256=rows[1][1], quote='Edward A. Fox')],
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(name)


if __name__ == '__main__':
    main()
