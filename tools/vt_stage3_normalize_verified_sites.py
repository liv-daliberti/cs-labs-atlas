"""Turn existing strict VT PI-site receipts into the Stage 3 audit schema.

Only the already fetched, name-matching sites with an exact link on a saved
official PI profile are integrated. Held sites and unsupported absences stay
open for manual review.
"""

import hashlib
import html.parser
import json
import re
import zlib
from urllib.parse import urljoin
from urllib.parse import urlsplit

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
    db = W.con('vt')
    accepted, held = [], []
    # The CS catalog's canonical person name retains the suffix period. The
    # source website ledger omitted it, leaving the same PI unaudited at g3.
    assert sum(r['pi'] in ('David H Smith IV', 'David H Smith IV.') for r in doc['labs']) == 1
    for site in doc['labs']:
        if site['pi'] == 'David H Smith IV':
            site['source_name'] = site['pi']
            site['pi'] = 'David H Smith IV.'
        name, url = site['pi'], site.get('url')
        if not (url and site.get('fetched') and site.get('names_person')
                and re.fullmatch(r'[0-9a-f]{64}', site.get('sha256') or '')):
            held.append(name)
            continue
        found = site.get('found_from') or {}
        source = found.get('url')
        if found.get('kind') != 'official_page' or not source:
            held.append(name)
            continue
        row = db.execute('select status,sha256,raw_zlib,fetched_at from live where url=?', (source,)).fetchone()
        if not row or row[0] != 200 or not row[2] or not (urlsplit(source).hostname or '').endswith('.vt.edu'):
            held.append(name)
            continue
        raw = zlib.decompress(row[2])
        assert hashlib.sha256(raw).hexdigest() == row[1], name
        if found.get('sha256') != row[1]:
            # The first capture predates the saved copy. Reconcile only when
            # the current official page still names the PI and links the site.
            body = W.flat(W.extract.blocks(raw, 'text/html', source))
            if name.split()[-1].rstrip('.') not in body:
                held.append(name)
                continue
        links = Links()
        links.feed(raw.decode('utf-8', 'replace'))
        exact = [urljoin(source, h) for h in links.hrefs
                 if L.normalized_link(urljoin(source, h)) == L.normalized_link(url)]
        if not exact:
            held.append(name)
            continue
        at = row[3][:10]
        if found.get('sha256') != row[1]:
            found['prior_sha256'] = found.get('sha256')
            found['sha256'] = row[1]
            found['reconciled_at'] = at
        site.update(
            reason_code='pi_homepage_only_no_lab_site', found_via='school_profile_link',
            listed_on=source, checked_at=at, audited_at=at,
            checks=[{'source': 'school_profile_link', 'url': url, 'on': source,
                     'result': 'listed', 'at': at, 'source_sha256': row[1], 'literal_href': exact[0]},
                    {'source': 'candidate_site', 'url': url, 'result': 'ok', 'at': at,
                     'sha256': site['sha256'], 'names_person': True}],
        )
        accepted.append(name)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'normalized': len(accepted), 'held': len(held), 'held_names': held}))


if __name__ == '__main__':
    main()
