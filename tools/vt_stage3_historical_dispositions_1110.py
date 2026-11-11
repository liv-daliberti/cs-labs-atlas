"""Record evidence-backed site dispositions for five historical VT PIs."""

import json
import zlib

import atlas_paths as P
import school_web as W


def main():
    path = P.data('lab-websites.json', 'vt')
    doc = json.loads(path.read_text())
    rows = {item['pi']: item for item in doc['labs']}
    db = W.con('vt')
    today = '2026-11-10'

    news = 'https://news.vt.edu/articles/2026/01/eng-cs-knapp-conferred-emeritus-status.html'
    r = db.execute('select status,sha256,raw_zlib from live where url=?', (news,)).fetchone()
    assert r and r[0] == 200 and 'professor emeritus' in zlib.decompress(r[2]).decode('utf-8', 'replace')
    doc['labs'].append(dict(pi='R. Benjamin Knapp', url=news, coverage='reason',
                            kind='emeritus_notice', reason_code='emeritus_or_admin_no_lab',
                            reason=('Virginia Tech conferred professor emeritus status in December 2025. '
                                    'The captured institutional notice documents the historical PI and retirement; '
                                    'it does not establish a current personal or lab homepage.'),
                            checked_at=today, audited_at=today,
                            checks=[dict(source='official_page', url=news, result='ok',
                                         at=today, sha256=r[1], quote='professor emeritus')]))

    profile = 'https://arc.vt.edu/about/our-team/nicholas-polys.html'
    r = db.execute('select status,sha256,raw_zlib from live where url=?', (profile,)).fetchone()
    assert r and r[0] == 200 and 'Nicholas F. Polys' in zlib.decompress(r[2]).decode('utf-8', 'replace')
    personal = 'https://people.cs.vt.edu/~npolys/'
    doc['labs'].append(dict(pi='Nicholas F. Polys', url=personal, coverage='reason',
                            kind='access_limited_personal_site', reason_code='host_access_blocked',
                            reason=('The official VT Advanced Research Computing profile confirms the person. '
                                    'The indexed VT personal homepage could not be captured because this crawler '
                                    'holds the host after an HTTP 403 elsewhere on it. This is an access outcome, '
                                    'not a finding that the homepage does not exist.'),
                            checked_at=today, audited_at=today,
                            checks=[dict(source='official_page', url=profile, result='ok',
                                         at=today, sha256=r[1], quote='Nicholas F. Polys'),
                                    dict(source='primary_search_index', url=personal,
                                         result='indexed_page', at=today,
                                         quote='Nicholas F. Polys, Ph.D.'),
                                    dict(source='candidate_site', url=personal,
                                         result='host_access_blocked', at=today)]))

    uva = [
        ('Christopher L. Barrett', 'christopher-l-barrett',
         'Christopher L. Barrett is the inaugural Distinguished Professor in Biocomplexity, Executive Director of the Biocomplexity Institute, and Professor in the Department of Computer Science at the University of Virginia.'),
        ('Madhav Marathe', 'madhav-marathe',
         'Madhav Marathe is an endowed Distinguished Professor in Biocomplexity, Executive Director of the Biocomplexity Institute, and a tenured Professor of Computer Science at the University of Virginia.'),
        ('Anil Vullikanti', 'anil-vullikanti',
         'He was at Virginia Tech from 2005 to 2018 and is a Professor of Computer Science at the University of Virginia.'),
    ]
    for name, slug, indexed_quote in uva:
        url = f'https://engineering.virginia.edu/faculty/{slug}'
        doc['labs'].append(dict(pi=name, url=url, coverage='reason',
                                kind='other_institution_profile', reason_code='site_at_other_institution',
                                reason=('The indexed official University of Virginia faculty page identifies the '
                                        'current UVA appointment. The primary host disallows this crawler; the '
                                        'index quote is retained as a lead, not a captured/verified lab website.'),
                                checked_at=today, audited_at=today,
                                checks=[dict(source='primary_search_index', url=url,
                                             result='official_profile_indexed', at=today,
                                             quote=indexed_quote),
                                        dict(source='candidate_site', url=url,
                                             result='robots_disallowed', at=today)]))
    assert all(sum(x['pi'] == name for x in doc['labs']) == 1 for name in
               ['R. Benjamin Knapp', 'Nicholas F. Polys', *(n for n, _, _ in uva)])
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'added': ['R. Benjamin Knapp', 'Nicholas F. Polys', *(n for n, _, _ in uva)]}))


if __name__ == '__main__':
    main()
