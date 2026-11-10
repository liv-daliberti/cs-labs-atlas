"""Add Cal Ribbens's official-profile-linked VT homepage to Stage 3."""

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
    f = P.data('lab-websites.json', 'vt')
    doc = json.loads(f.read_text())
    name = 'Cal Ribbens'
    if any(r['pi'] == name for r in doc['labs']):
        print('already reviewed')
        return
    source = 'https://website.cs.vt.edu/people/faculty/cal-ribbens.html'
    site = 'https://people.cs.vt.edu/ribbens/'
    db = W.con('vt')
    rows = [db.execute('select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (u,)).fetchone()
            for u in (source, site)]
    assert all(r and r[0] == 200 and r[2] for r in rows)
    for r in rows:
        assert hashlib.sha256(zlib.decompress(r[2])).hexdigest() == r[1]
    links = Links()
    links.feed(zlib.decompress(rows[0][2]).decode('utf-8', 'replace'))
    assert any(L.normalized_link(urljoin(source, h)) == L.normalized_link(site) for h in links.hrefs)
    text = W.flat(W.extract.blocks(zlib.decompress(rows[1][2]), rows[1][3], site))
    assert 'Calvin J. Ribbens' in text and 'Virginia Tech' in text
    at = rows[0][4][:10]
    doc['labs'].append(dict(
        pi=name, source_name='Calvin J. Ribbens', url=site, coverage='website',
        kind='pi_homepage', reason_code='pi_homepage_only_no_lab_site',
        found_from=dict(kind='official_page', url=source, sha256=rows[0][1]),
        found_via='school_profile_link', listed_on=source,
        fetched=True, sha256=rows[1][1], names_person=True,
        audited_at=at, checked_at=at,
        checks=[dict(source='school_profile_link', url=site, on=source,
                     result='listed', at=at, source_sha256=rows[0][1]),
                dict(source='candidate_site', url=site, result='ok', at=rows[1][4][:10],
                     sha256=rows[1][1], quote='Calvin J. Ribbens')],
    ))
    f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'historical_site_added': name, 'url': site}))


if __name__ == '__main__':
    main()
