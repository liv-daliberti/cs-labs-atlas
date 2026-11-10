"""Verify the saved VT person-page link to Adrian Sandu's lab site."""

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
    site = next(x for x in doc['labs'] if x['pi'] == 'Adrian Sandu')
    source = 'https://people.cs.vt.edu/~asandu/'
    url = 'https://csl.cs.vt.edu/'
    assert site['url'] == url
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
            for u in (source, url)]
    assert all(r and r[0] == 200 and r[2] for r in rows)
    raw = [zlib.decompress(r[2]) for r in rows]
    assert all(hashlib.sha256(b).hexdigest() == r[1] for b, r in zip(raw, rows))
    links = Links()
    links.feed(raw[0].decode('utf-8', 'replace'))
    exact = [urljoin(source, h) for h in links.hrefs
             if L.normalized_link(urljoin(source, h)) == L.normalized_link(url)]
    assert exact
    texts = [W.flat(W.extract.blocks(b, r[3], u)) for b, r, u in zip(raw, rows, (source, url))]
    assert 'Adrian Sandu' in texts[0]
    assert 'established in 2003 by Dr. Adrian Sandu' in texts[1]
    at = rows[0][4][:10]
    site.update(coverage='website', kind='lab_site', reason_code='lab_site',
                found_via='school_profile_link', listed_on=source,
                fetched=True, sha256=rows[1][1], names_person=True,
                checked_at=at, audited_at=at,
                checks=[dict(source='school_profile_link', url=url, on=source,
                             result='listed', at=at, source_sha256=rows[0][1], literal_href=exact[0]),
                        dict(source='candidate_site', url=url, result='ok', at=rows[1][4][:10],
                             sha256=rows[1][1], quote='established in 2003 by Dr. Adrian Sandu')])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'pi': 'Adrian Sandu', 'lab_site': url}))


if __name__ == '__main__':
    main()
