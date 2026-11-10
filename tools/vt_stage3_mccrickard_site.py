"""Replace a non-identifying project site with Scott McCrickard's VT homepage."""

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
    row = next(x for x in doc['labs'] if x['pi'] == 'Scott McCrickard')
    source = 'https://hci.icat.vt.edu/research-directory/people/scott-mccrickard.html'
    site = 'https://people.cs.vt.edu/~mccricks/'
    db = W.con('vt')
    saved = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
             for u in (source, site)]
    assert all(r and r[0] == 200 and r[2] for r in saved)
    raw = [zlib.decompress(r[2]) for r in saved]
    assert all(hashlib.sha256(b).hexdigest() == r[1] for b, r in zip(raw, saved))
    links = Links()
    links.feed(raw[0].decode('utf-8', 'replace'))
    exact = [urljoin(source, h) for h in links.hrefs
             if L.normalized_link(urljoin(source, h)) == L.normalized_link(site)]
    assert exact
    source_text = W.flat(W.extract.blocks(raw[0], saved[0][3], source))
    site_text = W.flat(W.extract.blocks(raw[1], saved[1][3], site))
    assert 'Scott Mccrickard' in source_text
    assert 'D. SCOTT MCCRICKARD' in site_text and 'Virginia Tech' in site_text
    at = saved[0][4][:10]
    row.update(url=site, coverage='website', kind='pi_homepage',
               reason_code='pi_homepage_only_no_lab_site',
               found_from=dict(kind='official_page', url=source, sha256=saved[0][1]),
               found_via='school_profile_link', listed_on=source,
               fetched=True, sha256=saved[1][1], names_person=True,
               checked_at=at, audited_at=at,
               checks=[dict(source='school_profile_link', url=site, on=source,
                            result='listed', at=at, source_sha256=saved[0][1], literal_href=exact[0]),
                       dict(source='candidate_site', url=site, result='ok', at=saved[1][4][:10],
                            sha256=saved[1][1], quote='D. SCOTT MCCRICKARD')])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'pi': row['pi'], 'homepage': site}))


if __name__ == '__main__':
    main()
