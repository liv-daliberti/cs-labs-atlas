"""Bind two historical VT faculty websites to saved university sources."""

import hashlib
import html.parser
import json
import subprocess
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


SITES = (
    ('Bert Huang', 'https://people.cs.vt.edu/~bhuang/BertHuangCV.pdf',
     'https://berthuang.com/', 'pi_homepage', 'pi_homepage_only_no_lab_site',
     'http://berthuang.com', 'Bert Huang', True),
    ('Daphne Yao', 'https://wordpress.cs.vt.edu/grweekend2021/schedule/',
     'https://yaogroup.cs.vt.edu/', 'lab_site', 'lab_site',
     'https://yaogroup.cs.vt.edu/', 'Yao Group', False),
)


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    existing = {row['pi'] for row in doc['labs']}
    db = W.con('vt')
    added = []
    for name, source, site, kind, reason, printed, quote, names_person in SITES:
        if name in existing:
            continue
        rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?',
                           (url,)).fetchone() for url in (source, site)]
        assert all(row and row[0] == 200 and row[2] for row in rows), name
        raw = [zlib.decompress(row[2]) for row in rows]
        assert all(hashlib.sha256(blob).hexdigest() == row[1] for blob, row in zip(raw, rows)), name
        if source.endswith('.pdf'):
            source_text = subprocess.run(['pdftotext', '-layout', '-', '-'], input=raw[0],
                                         capture_output=True, check=True).stdout.decode('utf-8', 'replace')
            assert printed in source_text, name
            source_kind = 'department_listing_link'
        else:
            source_text = W.flat(W.extract.blocks(raw[0], rows[0][3], source))
            links = Links()
            links.feed(raw[0].decode('utf-8', 'replace'))
            assert (any(L.normalized_link(urljoin(source, href)) == L.normalized_link(site)
                        for href in links.hrefs) or printed in source_text), name
            source_kind = 'department_listing_link'
        site_text = W.flat(W.extract.blocks(raw[1], rows[1][3], site))
        assert name.split()[-1] in source_text and quote in site_text, name
        at = rows[0][4][:10]
        doc['labs'].append(dict(
            pi=name, url=site, coverage='website', kind=kind, reason_code=reason,
            found_from=dict(kind='official_page', url=source, sha256=rows[0][1]),
            found_via=source_kind, listed_on=source,
            fetched=True, sha256=rows[1][1], names_person=names_person,
            audited_at=at, checked_at=at,
            checks=[dict(source=source_kind, url=site, on=source, result='listed',
                         at=at, source_sha256=rows[0][1], literal_href=printed),
                    dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                         sha256=rows[1][1], quote=quote)],
        ))
        added.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': added}))


if __name__ == '__main__':
    main()
