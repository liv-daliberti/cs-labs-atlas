#!/usr/bin/env python3
"""Yearly department-listing rows for a school's EXISTING census PIs, from the historical listing captures (HKUST, 2026-11-10).

listing_rows.py reads every archived directory capture, so its census would add every faculty member who left the school (HKUST: 142
persons, 125 of them PIs, against the 53 current ones the trial is built on). This keeps the census as it is and only adds the proven
listing years of those PIs: a row of `listings/<key>/rows.json` is a PI's when its profile account id (`profile/gchan`, `/~gchan/`,
`/faculty/scheng/`) is the account id of the PI's census profile URL. One row per (PI, department, year); the quote and capture are the
listing's own. A year with no ok capture stays unproven (listings/<key>/derived/coverage.json); nothing is bridged here.
-> listings/<key>/derived/listings.json (the file census_build.py writes, restricted to these PIs) and, in the census, each PI's years_listed,
   ranks_by_year and dated-listing sources (the census gates read them; the live 2026 rows stay)
usage: listing_pi_years.py <key>
"""
import collections
import json
import re
import sys

import atlas_paths as P  # noqa: E402

ACCOUNTS = [re.compile(r'/profile/([A-Za-z0-9_.-]+)'), re.compile(r'^profile/([A-Za-z0-9_.-]+)'), re.compile(r'/~([A-Za-z0-9_.-]+)'), re.compile(r'/faculty/([A-Za-z0-9_.-]+)/?$')]


def account(url):
    for rx in ACCOUNTS:
        m = rx.search(url or '')
        if m and m.group(1) not in ('profile', 'faculty'):
            return m.group(1).lower()
    return None


def main(key):
    census = json.loads(P.data('census-faculty.json', key).read_text())['faculty']
    pis = {account(x.get('profile_url')): x['name'] for x in census if x.get('is_pi') and account(x.get('profile_url'))}
    rows = json.loads(P.data('rows.json', key).read_text())
    by_dy, n = {}, collections.Counter()
    for r in rows:
        pi = pis.get(account(r.get('profile')))
        if not pi:
            n['rows_of_other_people'] += 1
            continue
        by_dy.setdefault((pi, r['dept'], r['year']), r)
    out = []
    for (pi, dept, year), r in sorted(by_dy.items(), key=lambda kv: (kv[0][0], kv[0][2])):
        out.append(dict(pi=pi, school=key, department=dept, year=year, capture_url=r['capture_url'], sha256=r['sha256'], quote=r['quote'],
                        rank_as_listed='; '.join(r['dept_title'] or r['titles']), rank=r['rank'], emeritus=r['rank'] == 'emeritus',
                        visiting=r['rank'] == 'visiting', observed=r['observed'], slot=r['slot']))
    P.data_w('listings.json', key).write_text(json.dumps(out, indent=0, ensure_ascii=False))
    doc = json.loads(P.data('census-faculty.json', key).read_text())
    by_pi = collections.defaultdict(list)
    for r in out:
        by_pi[r['pi']].append(r)
    for x in doc['faculty']:
        rs = by_pi.get(x['name'])
        if not rs:
            continue
        x['years_listed'] = sorted({r['year'] for r in rs} | set(x.get('years_listed') or []))
        rk = collections.defaultdict(set)
        for r in rs:
            rk[str(r['year'])].add(r['rank'])
        for y, v in (x.get('ranks_by_year') or {}).items():
            rk[y] |= set(v)
        x['ranks_by_year'] = {y: sorted(v) for y, v in sorted(rk.items())}
        have = {(q.get('url'), q.get('sha256')) for q in x.get('sources') or []}
        x['sources'] = list(x.get('sources') or []) + [dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], kind=f"dept_listing:{r['department']}", observed=r['observed'],
                                                            rank_as_listed=r['rank_as_listed'], rank=r['rank'], slot=r['slot']) for r in rs if (r['capture_url'], r['sha256']) not in have]
    P.data_w('census-faculty.json', key).write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    years = collections.defaultdict(set)
    for r in out:
        years[r['pi']].add(r['year'])
    print(json.dumps(dict(pis=len(pis), pis_with_rows=len(years), rows=len(out), **n)))


if __name__ == '__main__':
    main(sys.argv[1])
