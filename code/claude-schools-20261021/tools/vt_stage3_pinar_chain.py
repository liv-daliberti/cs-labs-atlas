"""Verify VT profile -> Pinar Yanardag page -> GEM Lab site."""

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
    site = next(x for x in doc['labs'] if x['pi'] == 'Pinar Yanardag')
    official = 'https://sanghani.cs.vt.edu/people/our-team/faculty/pinar-yanardag.html'
    pi_page = 'https://pinguar.org'
    lab = 'https://gemlab-vt.github.io/'
    assert site['url'] == lab
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
            for u in (official, pi_page, lab)]
    assert all(r and r[0] == 200 and r[2] for r in rows)
    raw = [zlib.decompress(r[2]) for r in rows]
    assert all(hashlib.sha256(b).hexdigest() == r[1] for b, r in zip(raw, rows))
    links = []
    for b in raw[:2]:
        parser = Links()
        parser.feed(b.decode('utf-8', 'replace'))
        links.append(parser.hrefs)
    hrefs = []
    for source, target, candidates in ((official, pi_page, links[0]), (pi_page, lab, links[1])):
        exact = [h for h in candidates if L.normalized_link(urljoin(source, h)) == L.normalized_link(target)]
        assert exact, source
        hrefs.append(exact[0])
    texts = [W.flat(W.extract.blocks(b, r[3], u)) for b, r, u in zip(raw, rows, (official, pi_page, lab))]
    assert all('Pinar Yanardag' in t for t in texts)
    assert 'GEM Lab' in texts[2]
    at = rows[0][4][:10]
    chain = [dict(source_url=source, url=target, href=href,
                  source_sha256=row[1], source_fetched_at=row[4])
             for source, target, href, row in ((official, pi_page, hrefs[0], rows[0]),
                                               (pi_page, lab, hrefs[1], rows[1]))]
    site.update(coverage='website', kind='lab_site', reason_code='lab_site',
                found_via='official_link_chain', listed_on=official,
                sha256=rows[2][1], fetched=True, names_person=True,
                checked_at=at, audited_at=at,
                checks=[dict(source='official_link_chain', url=lab, on=official,
                             result='listed', at=at, provenance_chain=chain),
                        dict(source='candidate_site', url=lab, result='ok',
                             at=rows[2][4][:10], sha256=rows[2][1], quote='Pinar Yanardag')])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'verified_chain': 'Pinar Yanardag', 'url': lab}))


if __name__ == '__main__':
    main()
