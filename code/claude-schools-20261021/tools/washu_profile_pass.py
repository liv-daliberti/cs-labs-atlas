"""WashU stage-3 profile pass (2026-11-15): two official profile pages, fetched live (robots honoured, >= 3 s between requests, no archive.org), decide
two website-register rows; the other four open official-link PIs stay held.

  washu_profile_pass.py fetch    --out <json>                      refetch the profiles below once and the chain's stub and target once each
  washu_profile_pass.py register --profiles <json> --src <register> --out <register>   write the DECISIONS rows

Held (no profile page exists to read, so no row is written):
  Ron Cytron, Ulugbek Kamilov, Chenguang Wang: not listed in the current cse.washu.edu directory (49 faculty); engineering.washu.edu/faculty/<First-Last>.html and
      cse.washu.edu/faculty-research/faculty/<First-Last>.html are 404 (2026-11-07 and 2026-11-15); engineering.wustl.edu answers 310 (redirect, queued for review).
  Neal Patwari: ese.washu.edu lists him as an adjunct with a mailto only (no profile card); both profile slugs 404.
  Bruno Sinopoli: in no current directory; both profile slugs 404.
Run with CS_ATLAS_HIERARCHY pointing at a scratch overlay holding a copy of washu/raw/school-captures.sqlite: the fetch writes there, never to main.
"""
import argparse
import json
import re
import zlib
from pathlib import Path

import school_web as W  # noqa: E402
from profile_pass_people_directory import SCOPE, STALE, utc_of  # noqa: E402

KEY = 'washu'
GAP = 3.0
PROFILE = 'https://engineering.washu.edu/faculty/{slug}.html'
# Jiaxin Huang: the profile links Google Scholar and a CV only -> an absence row. Ning Zhang: the profile's "Lab website" is a stub page
# that redirects to the lab site; profile -> stub -> lab is a literal two-hop href chain.
DECISIONS = {
    'Jiaxin Huang': dict(slug='Jiaxin-Huang', kind='absence', seen='a Google Scholar profile (an identity index, not a site) and a CV download only'),
    'Ning Zhang': dict(slug='Ning-Zhang', kind='chain', stub='https://n1ngz.github.io/', lab='https://cybersecurity.seas.wustl.edu'),
}


def hrefs(raw):
    return re.findall(r'<a [^>]*href="([^"]+)"', raw)


def fetch(out):
    c = W.con(KEY)
    res = {}
    for n, d in DECISIONS.items():
        urls = [PROFILE.format(slug=d['slug'])] + ([d['stub'], d['lab']] if d['kind'] == 'chain' else [])
        for i, u in enumerate(urls):
            W.live(c, u, refresh=(i == 0), min_delay=GAP)
            row = c.execute('select status, sha256, fetched_at, raw_zlib from live where url=?', (u,)).fetchone()
            raw = zlib.decompress(row[3]).decode('utf-8', 'replace') if row and row[3] else ''
            res.setdefault(n, {})[u] = dict(status=row[0], sha256=row[1], fetched_at=row[2], hrefs=hrefs(raw), names_pi=n.split()[-1] in raw)
            print(n, u, row[0], flush=True)
    Path(out).write_text(json.dumps(res, indent=1) + '\n')


def register(profiles, src, out):
    prof = json.loads(Path(profiles).read_text())
    doc = json.loads(Path(src).read_text())
    rows = {r['pi']: r for r in doc['labs']}
    for n, d in DECISIONS.items():
        pu = PROFILE.format(slug=d['slug'])
        p = prof[n][pu]
        assert p['status'] == 200 and p['names_pi'], n
        at = utc_of(p['fetched_at'])
        r = rows[n]
        checks = [c for c in r['checks'] if not (c['source'] == 'school_profile' and c.get('url') == pu)]
        checks.append(dict(source='school_profile', url=pu, at=at, result='ok', sha256=p['sha256']))
        places = set(r.get('places_checked') or []) | {'school_profile:ok'}
        if d['kind'] == 'absence':
            assert not [h for h in p['hrefs'] if 'github.io' in h or '~' in h], n
            for k in STALE:
                r.pop(k, None)
            places.add('school_profile_link:none')
            r.update(status='none_found', reason_code='profile_only_no_homepage', coverage='reason', reason_type='profile_fetched_no_lab_link', reason_scope=SCOPE,
                     reason=(f"The PI's official engineering.washu.edu profile ({pu}) was fetched live on {at[:10]} (robots honoured, no archive.org) and links no lab or personal "
                             f"website (it shows {d['seen']}); no other source was read for this row. " + SCOPE),
                     upstream_audit_reason='only the department profile exists; it links no homepage or lab site', evidence_gaps=[])
        else:
            st, lab = prof[n][d['stub']], prof[n][d['lab']]
            assert st['status'] == 200 and lab['status'] == 200 and d['stub'] in p['hrefs'] and d['lab'] in st['hrefs'], n
            chain = [dict(source_url=pu, url=d['stub'], href=d['stub'], anchor='Lab website', source_sha256=p['sha256'], source_fetched_at=at, source_capture_url=None, via='literal_html_href'),
                     dict(source_url=d['stub'], url=d['lab'], linked_url=d['lab'], href=d['lab'], anchor='WUSTL', source_sha256=st['sha256'], source_fetched_at=utc_of(st['fetched_at']),
                          source_capture_url=None, via='literal_html_href')]
            link = dict(source='official_link_chain', url=d['lab'], on=pu, at=at, result='listed_via_recorded_chain', original_link=d['stub'], provenance_chain=chain,
                        provenance='live_profile_fetch_2026-11-15')
            checks.append(link)
            places |= {'official_link_chain:listed_via_recorded_chain'}
            r.update(url=d['lab'], sha256=lab['sha256'], found_via='official_link_chain', listed_on=pu, official_link_status='recorded', official_link_evidence=[link])
            r['evidence'] = dict(r['evidence'], url=d['lab'], sha256=lab['sha256'])
            r['checks'] = checks
        r['checks'] = checks
        r['places_checked'] = sorted(places)
        r['checked_at'] = max(r.get('checked_at') or '', at)
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(len(DECISIONS), 'rows written')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['fetch', 'register'])
    ap.add_argument('--profiles')
    ap.add_argument('--src')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    fetch(a.out) if a.cmd == 'fetch' else register(a.profiles, a.src, a.out)


if __name__ == '__main__':
    main()
