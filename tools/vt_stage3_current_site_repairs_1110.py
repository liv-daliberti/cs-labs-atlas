"""Repair three current VT PI site audits from captured official links and access results."""

import json
import zlib

import atlas_paths as P
import school_web as W


def live(db, url):
    row = db.execute('select status,sha256,fetched_at,raw_zlib from live where url=?', (url,)).fetchone()
    assert row and row[1] and row[2], url
    return row


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    rows = {item['pi']: item for item in doc['labs']}
    db = W.con('vt')
    today = '2026-11-10'

    name = 'Huaicheng Li'
    official = 'https://website.cs.vt.edu/people/faculty/huaicheng-li.html'
    intermediate = 'https://people.cs.vt.edu/~huaicheng/'
    site = 'https://huaicheng.github.io/'
    a, b, c = (live(db, url) for url in (official, intermediate, site))
    assert a[0] == b[0] == c[0] == 200
    assert intermediate in zlib.decompress(a[3]).decode('utf-8', 'replace')
    assert 'https://huaicheng.github.io' in zlib.decompress(b[3]).decode('utf-8', 'replace')
    assert 'Huaicheng Li' in zlib.decompress(c[3]).decode('utf-8', 'replace')
    rows[name].update(url=site, coverage='website', kind='pi_homepage',
                      reason_code='pi_homepage_only_no_lab_site', fetched=True,
                      sha256=c[1], names_person=True, found_via='official_link_chain',
                      listed_on=official, checked_at=today, audited_at=today,
                      checks=[dict(source='official_link_chain', url=site, on=official,
                                   result='listed', at=today,
                                   provenance_chain=[
                                       dict(source_url=official, url=intermediate, href=intermediate,
                                            source_sha256=a[1], source_fetched_at=a[2]),
                                       dict(source_url=intermediate, url=site,
                                            href='https://huaicheng.github.io',
                                            source_sha256=b[1], source_fetched_at=b[2])]),
                              dict(source='candidate_site', url=site, result='ok',
                                   at=today, sha256=c[1], names_person=True)])

    for name, profile, selected, blocked in [
        ('Kurt Luther', 'https://website.cs.vt.edu/people/faculty/kurt-luther.html',
         'https://people.cs.vt.edu/kluther/newlab/kurt-luther.html',
         'https://crowd.cs.vt.edu/kurt-luther/'),
        ('Xun (Steve) Jian', 'https://website.cs.vt.edu/people/faculty/xun-jian.html',
         'https://people.cs.vt.edu/xunj/PC/homepage.html',
         'https://people.cs.vt.edu/xunj/'),
    ]:
        p = live(db, profile)
        assert p[0] == 200
        # The captured official profile supplies a site lead, but the direct
        # lab/home route is denied by robots; never call that a verified site.
        official_lead = ('https://crowd.cs.vt.edu/kurt-luther/' if name == 'Kurt Luther'
                         else selected)
        assert official_lead in zlib.decompress(p[3]).decode('utf-8', 'replace')
        row = rows[name]
        row.update(coverage='reason', reason_code=('host_blocked_by_robots' if name == 'Kurt Luther'
                                                   else 'host_access_blocked'),
                   reason=('The official VT faculty profile links a PI site, but the linked host '
                           'disallows this research crawler. A different candidate URL has not '
                           'been promoted without an official link chain.'),
                   reason_type='access_blocked', checked_at=today, audited_at=today,
                   checks=[dict(source='school_profile_link', url=official_lead,
                                on=profile, result='listed', at=today,
                                source_sha256=p[1], literal_href=official_lead),
                           dict(source='candidate_site', url=blocked,
                                result='robots_disallowed', at=today)])
        # Preserve the candidate URL and capture as a lead, while the audit
        # explicitly marks it as unverified for this gate.
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'verified': ['Huaicheng Li'], 'access_blocked': ['Kurt Luther', 'Xun (Steve) Jian']}))


if __name__ == '__main__':
    main()
