"""Georgia Tech stage-3 profile pass (2026-11-15): the websites a PI's own official gatech.edu profile page links.

Why: the website register needs, for every PI whose site was found by a non-official source, an official link (the PI's department profile links it) or,
when the profile was actually read and links no lab or personal site, a dated absence row (profile-first ruling). A PI whose profile page cannot be read
(no page, host refusal, challenge) stays held; nothing here defaults to `no_web_presence_found`.

  profile_pass_gatech.py parse  --names <json {pi: profile url}> --store <captures sqlite> --out <json>   read the STORED profile pages (no network)
  profile_pass_gatech.py fetch  --names <json {pi: profile url}> --store <captures sqlite> --out <json>   fetch each profile once (robots honoured, >= 3 s per host, a host that
                                                                 answers a refusal or challenge is never retried) into a scratch store, then parse
  profile_pass_gatech.py sites  --names <json {pi: url}> --store <captures sqlite> --out <json>          fetch each profile-linked site's front page once (a redirect is
                                                                 recorded, never followed; the exact target is fetched only when --follow lists it)

Per name: url, status, sha256, fetched_at, h1, names_pi (the page's heading or title carries the surname) and links (the anchors under the profile that are not site
chrome: social media, footers, listing and department pages).
"""
import argparse
import html
import json
import re
import sqlite3
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urljoin, urlsplit

GAP = 3.0
CHROME_HOST = re.compile(r'(?:^|\.)(?:facebook|instagram|flickr|youtube|linkedin|twitter|x|tiktok|maps\.app\.goo|goo|gbi\.georgia|ethicspoint|gatechhotel|bncollege|'
                         r'georgia\.gov|usg\.edu|gatech|ibm|w3|schema)\.(?:com|gl|gov|edu|org|app\.goo\.gl)$|^(?:www\.)?(?:x\.com|facebook\.com|twitter\.com)$', re.I)
ANCH = re.compile(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()


def clean(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()


def parse_page(raw, url, name):
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.S)
    title = re.search(r'<title>(.*?)</title>', raw, re.S)
    head = clean(h1.group(1)) if h1 else None
    sur = fold(re.sub(r'[()"]', '', name).split()[-1])
    names_pi = bool(sur and (sur in fold(head or '') or sur in fold(clean(title.group(1)) if title else '')))
    body = raw
    for marker in ('<footer', 'id="footer"', 'class="footer'):
        i = body.find(marker)
        if i > 0:
            body = body[:i]
    links = []
    for href, inner in ANCH.findall(body):
        u = urljoin(url, html.unescape(href))
        sp = urlsplit(u)
        if sp.scheme not in ('http', 'https') or not sp.hostname:
            continue
        links.append(dict(href=u, text=clean(inner)[:80]))
    return head, names_pi, links


def con(store):
    c = sqlite3.connect(store)
    c.execute('create table if not exists live (url text primary key, fetched_at text, status int, sha256 text, content_type text, raw_zlib blob, text text)')
    return c


def run(names, store, out_path, fetch):
    import school_web as W  # noqa: E402  (its container is the school's raw/school-captures.sqlite under CS_ATLAS_HIERARCHY)
    c = W.con('gatech') if fetch else None
    ro = sqlite3.connect(f'file:{store}?mode=ro', uri=True)
    res = {}
    for n, url in names.items():
        row = dict(name=n, url=url)
        if fetch:
            W.live(c, url, min_delay=GAP)
        r = ro.execute('select status, sha256, fetched_at, raw_zlib from live where url=?', (url,)).fetchone() if not fetch else \
            c.execute('select status, sha256, fetched_at, raw_zlib from live where url=?', (url,)).fetchone()
        if not r:
            row.update(status=None, note='no stored page (not fetched: robots disallow, blocked host, or not requested)')
        else:
            row.update(status=r[0], sha256=r[1], fetched_at=r[2])
            if r[0] == 200 and r[3]:
                head, names_pi, links = parse_page(zlib.decompress(r[3]).decode('utf8', 'replace'), url, n)
                row.update(h1=head, names_pi=names_pi, links=links)
        res[n] = row
        print(n, row.get('status'), row.get('names_pi'), flush=True)
    Path(out_path).write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')


def sites(pairs, out_path):
    """Fetch each {pi: url} once (robots honoured, >= 3 s per host); a redirect is recorded (location) and never followed."""
    import school_web as W  # noqa: E402
    c = W.con('gatech')
    res = {}
    for n, url in pairs.items():
        W.live(c, url, min_delay=GAP)
        r = c.execute('select status, sha256, fetched_at, raw_zlib from live where url=?', (url,)).fetchone()
        row = dict(name=n, url=url)
        if not r:
            row.update(status=None, note='not fetched (robots disallow or blocked host)')
        else:
            row.update(status=r[0], sha256=r[1], fetched_at=r[2])
            body = zlib.decompress(r[3]) if r[3] else b''
            txt = body.decode('utf-16' if body[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf8', 'replace')
            if 300 <= (r[0] or 0) < 400:
                row['location'] = json.loads(body).get('location')
            else:
                t = re.search(r'<title[^>]*>(.*?)</title>', txt, re.S | re.I)
                row['title'] = clean(t.group(1)) if t else None
                row['meta_refresh'] = (re.search(r'http-equiv="refresh"[^>]*content="([^"]*)"', txt, re.I) or [None, None])[1]
                sur = fold(re.sub(r'[()"]', '', n).split()[-1])
                row['names_pi'] = sur in fold(clean(txt))
                row['quote'] = clean(txt)[:80] if row['names_pi'] else None
        res[n] = row
        print(n, row.get('status'), row.get('location') or row.get('title'), flush=True)
    Path(out_path).write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')


SITE, ABSENCE = 'site', 'absence'
SCOPE = 'Recorded search/access outcome; not proof no website exists or that an archive has no capture.'
NONE = 'nothing (no website field or personal link)'
# profile page read live (or from the page stored by the same tool run) and naming the PI; held PIs are NOT listed: a profile that cannot be read, whose page names
# someone else, whose linked site sits behind a robots redirect/refusal or cannot be connected to, or whose host answered a refusal, stays open.
# SITE: `linked` is the anchor exactly as the profile shows it, `chain` the redirects of that URL (each hop fetched once from its exact Location), `target` the fetched final page.
DECISIONS = {
    'Beki Grinter': dict(kind=SITE, linked='http://www.grinter.org', code='pi_homepage_only_no_lab_site', target='https://www.grinter.org/Welcome.html', chain=['https://www.grinter.org (meta refresh to Welcome.html)']),
    'Matthieu Ratoslav Bloch': dict(kind=SITE, linked='http://users.ece.gatech.edu/~mbloch', code='pi_homepage_only_no_lab_site', target='https://bloch.ece.gatech.edu',
                                    chain=['https://users.ece.gatech.edu/~mbloch 301 http://users.ece.gatech.edu/mbloch', 'https://users.ece.gatech.edu/mbloch 302 http://bloch.ece.gatech.edu']),
    'Sung Kyu Lim': dict(kind=SITE, linked='http://users.ece.gatech.edu/~limsk', code='pi_homepage_only_no_lab_site', target='https://limsk.ece.gatech.edu',
                         chain=['https://users.ece.gatech.edu/~limsk 301 http://users.ece.gatech.edu/limsk', 'https://users.ece.gatech.edu/limsk 302 http://limsk.ece.gatech.edu']),
    'Vincent J Mooney': dict(kind=SITE, linked='http://users.ece.gatech.edu/~mooney', code='pi_homepage_only_no_lab_site', target='https://mooney.gatech.edu',
                             chain=['https://users.ece.gatech.edu/~mooney 301 http://users.ece.gatech.edu/mooney', 'https://users.ece.gatech.edu/mooney 302 http://mooney.gatech.edu']),
    'Jennifer Olson Hasler': dict(kind=SITE, linked='http://hasler.ece.gatech.edu', code='lab_site', target='https://hasler.ece.gatech.edu'),
    'Julie Linsey': dict(kind=SITE, linked='https://sites.google.com/site/idreemlaboratory/', code='lab_site', target='https://sites.google.com/site/idreemlaboratory/'),
    'Mustaque Ahamad': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Shabbir Ahmed': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Hyesoon Kim': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Abhijit Chatterjee': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Bonnie H Ferri': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Linda S Milor': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Patricio Antonio Vela': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Erik I Verriest': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Frank Li': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only a job advertisement and a newsletter sign-up of the School of Cybersecurity and Privacy'),
    'Cedric Pradalier': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Fabian Monrose': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Pan Li': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Yalong Yang': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Bo Zhu': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Cindy Kaiying Lin': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only archived publisher pages of her publications'),
    'Edward J Coyle': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only the contact page vip.gatech.edu/contact of the Vertically Integrated Projects program (not a lab or personal site)'),
    'Arthur Delarue': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only a Google Scholar profile (an identity index, not a site)'),
    'Mark Guzdial': dict(kind=ABSENCE, code='site_at_other_institution', seen='only his site guzdial.engin.umich.edu at the University of Michigan'),
    'David W. Rosen': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Ye-Hwa Chen': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Nader Sadegh': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only a US patent record'),
    'Roger Jianxin Jiao': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='only a Google Scholar profile (an identity index, not a site)'),
    'Jay David Bolter': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
    'Glaucio H. Paulino': dict(kind=ABSENCE, code='profile_only_no_homepage', seen=NONE),
}
STALE = ('url', 'kind', 'sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'verified', 'verified_by', 'verification_reason',
         'verification_quote', 'unverified_reason', 'official_link_status', 'official_link_evidence', 'rejected_url', 'rejected_reason', 'review_note', 'website_note')


def utc_of(local):
    """The live table stamps fetched_at in the node's local time (America/New_York); the registers keep UTC."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%S+00:00')


def register(profile_paths, sites_paths, reg_in, reg_out):
    prof = {}
    for pp in profile_paths:
        prof.update(json.loads(Path(pp).read_text()))
    fetched = {}
    for sp in sites_paths:
        for n, r in json.loads(Path(sp).read_text()).items():
            fetched.setdefault(n, []).append(r)
    doc = json.loads(Path(reg_in).read_text())
    rows = {r['pi']: r for r in doc['labs']}
    changed = []
    for n, dec in DECISIONS.items():
        p = prof[n]
        assert p['status'] == 200 and p['names_pi'], n
        r = rows.setdefault(n, dict(pi=n))
        earlier = (r.get('url'), r.get('found_via'))
        for k in STALE:
            r.pop(k, None)
        prof_at = utc_of(p['fetched_at'])
        checks = [c for c in (r.get('checks') or []) if not (c.get('source') in ('school_profile', 'school_profile_link') and c.get('at') == prof_at)]
        checks.append(dict(source='school_profile', url=p['url'], at=prof_at, result='ok', sha256=p['sha256']))
        places = set(r.get('places_checked') or []) | {'school_profile:ok'}
        host = urlsplit(p['url']).netloc
        if dec['kind'] == ABSENCE:
            places.add('school_profile_link:none')
            was = f" An earlier audit had selected {earlier[0]} (found via {earlier[1]}); no official page links it, so it is not recorded as the lab website." if earlier[0] else ''
            r.update(status='none_found', reason_code=dec['code'], coverage='reason', reason_type='profile_fetched_no_lab_link', reason_scope=SCOPE,
                     reason=(f"The PI's official profile ({p['url']}) was fetched live on {prof_at[:10]} (robots honoured, no archive.org) and links no lab or personal "
                             f"website (it shows {dec['seen']}); no other source was read in this pass." + was + ' ' + SCOPE),
                     upstream_audit_reason='only the department profile exists; it links no homepage or lab site', evidence_gaps=[])
            r.pop('rejected_reason', None)
        else:
            s = next(x for x in fetched[n] if x['status'] == 200 and x['url'] == dec['target'])
            url = dec['linked']
            assert any(l['href'].rstrip('/') == url.rstrip('/') for l in p['links']), (n, url)
            link = dict(source='school_profile_link', url=url, on=p['url'], at=prof_at, result='listed', anchor=url, linked_url=url,
                        source_sha256=p['sha256'], source_capture_url=None, provenance='live_profile_fetch_2026-11-15')
            cand = dict(source='candidate_site', url=url, at=utc_of(s['fetched_at']), via='school_profile_link', sha256=s['sha256'],
                        result='ok' if s['names_pi'] else 'does_not_name_pi_kept_strong_source')
            if s['url'] != url:
                cand['final_url'] = s['url']
            if dec.get('chain'):
                cand['redirect_chain'] = dec['chain']
            checks += [link, cand]
            places |= {'school_profile_link:listed', 'candidate_site:' + cand['result']}
            r.update(status='found', reason_code=dec['code'], coverage='website', url=url, kind='lab_site' if dec['code'] == 'lab_site' else 'pi_homepage',
                     found_via='school_profile_link', listed_on=p['url'], sha256=s['sha256'],
                     evidence=dict(url=s['url'], sha256=s['sha256'], quote=s['quote']), official_link_status='recorded', official_link_evidence=[link],
                     reason='Captured lab/group website.' if dec['code'] == 'lab_site' else "no lab site; the PI's own homepage is the lab page",
                     upstream_audit_reason="the PI's own official profile links this site (fetched live 2026-11-15)", evidence_gaps=[])
        r['checks'] = checks
        r['places_checked'] = sorted(places)
        r['checked_at'] = prof_at
        r.setdefault('audited_at', prof_at)
        r.setdefault('students_page_status', 'not_audited_in_this_pass')
        r.setdefault('papers_page_status', 'not_audited_in_this_pass')
        changed.append(n)
    doc['labs'] = [rows[x['pi']] for x in doc['labs']] + [r for n, r in rows.items() if n not in {x['pi'] for x in doc['labs']}]
    Path(reg_out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(len(changed), 'rows written')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['parse', 'fetch', 'sites', 'register'])
    ap.add_argument('--names')
    ap.add_argument('--store')
    ap.add_argument('--profiles', nargs='*', default=[], help='register: the parse/fetch outputs')
    ap.add_argument('--sites', nargs='*', default=[], help='register: the sites outputs')
    ap.add_argument('--src', help='register: the register to start from')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'register':
        return register(a.profiles, a.sites, a.src, a.out)
    if a.cmd == 'sites':
        return sites(json.loads(Path(a.names).read_text()), a.out)
    run(json.loads(Path(a.names).read_text()), a.store, a.out, a.cmd == 'fetch')


if __name__ == '__main__':
    main()
