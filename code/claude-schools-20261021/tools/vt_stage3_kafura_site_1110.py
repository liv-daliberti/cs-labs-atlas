"""Record the VT-hosted Dennis Kafura homepage and its official project-team link."""

import hashlib
import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    assert not any(row['pi'] == 'Dennis Kafura' for row in doc['labs'])
    site = 'https://people.cs.vt.edu/~kafura/'
    official = 'https://think.cs.vt.edu/about'
    row = W.con('vt').execute(
        'select status,sha256,raw_zlib,content_type,fetched_at from live where url=?', (site,)
    ).fetchone()
    assert row and row[0] == 200 and row[2]
    raw = zlib.decompress(row[2])
    assert hashlib.sha256(raw).hexdigest() == row[1]
    body = W.flat(W.extract.blocks(raw, row[3], site))
    assert 'Dennis Kafura' in body and '[email removed]' in body
    checked = row[4][:10]
    doc['labs'].append(dict(
        pi='Dennis Kafura', url=site, coverage='website', kind='pi_homepage',
        reason_code='pi_homepage_only_no_lab_site',
        found_via='department_listing_link', listed_on=official,
        sha256=row[1], checked_at=checked, audited_at=checked,
        reason='Captured VT-hosted professor-emeritus personal webpage.',
        checks=[
            dict(source='candidate_site', url=site, result='ok', at=checked,
                 sha256=row[1], quote='Dennis Kafura Professor Emeritus'),
            dict(source='department_listing_link', url=site, on=official,
                 result='ok', at=checked,
                 quote='Dennis Kafura | Professor | Status: Professor (Computer Science) at Virginia Tech | Website: people.cs.vt.edu/~kafura/',
                 access='official VT CS project-team page reviewed through web index; direct capture blocked by robots'),
        ],
    ))
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print('Dennis Kafura: VT site and direct official project-team link recorded')


if __name__ == '__main__':
    main()
