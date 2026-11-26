"""Profile links for PIs the website register does not yet cover (JHU deep dive, websites step).

A unit directory (department faculty page, stored Wayback capture) links each person's profile; that link is a PI's official profile URL, found_from the directory
capture (url + sha256 + anchor text). Nothing is guessed from a name pattern. The profile host is Wayback-only (bot challenge) unless the charter says otherwise, so
the row is fetched=false with that reason; nothing is fetched here.
reads   the school capture store (departments of the charter's affiliated units and 'jhu'), pis.json, person-websites.json
writes  rows appended to person-websites.json (kind pi_profile, verified=false, found_from_kind official_page); a PI with no directory link gets no row
usage   jhu_unit_links.py build jhu [--dry]
"""
import json
import re
import sys

import atlas_paths as P  # noqa: E402
import person_websites as PW  # noqa: E402
import school_web as W  # noqa: E402

PROFILE = re.compile(r'^https?://(?:www\.)?(?:[a-z-]+\.)?jhu\.edu/[^?#]*(?:faculty|people|profile|person|directory)[^?#]*/[^/?#]+/?$', re.I)
DIRECTORY = re.compile(r'/(?:faculty|people)/?$', re.I)


def build(school, dry=False):
    pis = json.loads(P.data('pis.json', school).read_text())
    path = P.data('person-websites.json', school)
    doc = json.loads(path.read_text())
    have = {r['person'] for r in doc['rows'] if r['kind'] == 'pi_profile'}
    keys = {}
    for p in pis:
        if p['pi'] not in have:
            for n in [p['pi']] + list(p.get('names') or []):
                k = PW.name_key(n)
                if k:
                    keys.setdefault(k, p['pi'])
    c = W.con(school)
    best = {}
    for cap, page, ts, sha, raw in c.execute("select capture_url, page_url, wayback_timestamp, sha256, raw_zlib from captures where http_status=200 and raw_zlib is not null "
                                             "and department not like 'homepage%' and department not like 'student%' and department not like 'defense%'"):
        if not DIRECTORY.search(PW.original(page or cap).split('?')[0]):
            continue
        html_ = W.body(raw)
        for href, text in PW.page_anchors(html_, PW.original(cap)):
            k = PW.name_key(text)
            if not k or k not in keys or not PROFILE.match(PW.original(href)):
                continue
            who = keys[k]
            old = best.get(who)
            if not old or str(ts) > old[0]:
                best[who] = (str(ts), re.sub(r':80/', '/', PW.original(href)), PW.original(cap), sha, text)
    rows = []
    for who, (ts, url, page, sha, text) in sorted(best.items()):
        rows.append(dict(person=who, role='pi', lab=who, kind='pi_profile', url=url,
                         found_from=dict(kind='official_page', url=page, sha256=sha, anchor=text, observed=ts),
                         fetched=False, fetch_reason='host answers bot challenges (Wayback only); recorded from the official directory that links it, queued',
                         found_from_kind='official_page', verified=False))
    if not dry:
        doc['rows'] += rows
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return len(pis), len(have), rows


if __name__ == '__main__':
    n, h, rows = build(sys.argv[2], '--dry' in sys.argv)
    print(f'pis {n}, already with a profile {h}, new profile rows {len(rows)}, PIs still without {n - h - len(rows)}')
