"""Finish Steven Flammia's VT official-link website audit."""

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
    source = 'https://iac.vt.edu/about/faculty/flammia-steven.html'
    site = 'https://sflammia.github.io/'
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                       (url,)).fetchone() for url in (source, site)]
    assert all(row and row[0] == 200 and row[2] for row in rows)
    raw = [zlib.decompress(row[2]) for row in rows]
    assert all(hashlib.sha256(blob).hexdigest() == row[1] for blob, row in zip(raw, rows))
    links = Links()
    links.feed(raw[0].decode('utf-8', 'replace'))
    assert any(L.normalized_link(urljoin(source, href)) == L.normalized_link(site)
               for href in links.hrefs)
    site_text = W.flat(W.extract.blocks(raw[1], rows[1][3], site))
    assert 'Steven Flammia Professor, Virginia Tech' in site_text
    row = next(row for row in doc['labs'] if row['pi'] == 'Steven Flammia')
    at = rows[0][4][:10]
    row.update(url=site, coverage='website', kind='pi_homepage',
               reason_code='pi_homepage_only_no_lab_site', found_via='school_profile_link',
               listed_on=source, fetched=True, sha256=rows[1][1], names_person=True,
               audited_at=at, checked_at=at,
               checks=[dict(source='school_profile_link', url=site, on=source,
                            result='listed', at=at, source_sha256=rows[0][1], literal_href=site),
                       dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                            sha256=rows[1][1], quote='Steven Flammia Professor, Virginia Tech')])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('Steven Flammia')


if __name__ == '__main__':
    main()
