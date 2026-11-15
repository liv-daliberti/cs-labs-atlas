"""EPFL stage-3 profile pass (2026-11-15): one live people.epfl.ch profile page per PI, robots honoured, >= 3 s between requests, no archive.org.

Why: the stage-3 gate for EPFL lacks (a) a reviewed home department for PIs whose census row names no school (the home is the school/institute of
the profile position's unit, read from the page's own breadcrumb EPFL > SCHOOL > INSTITUTE > UNIT) and (b) official-link / absence records for lab
websites. Both are read from the PI's own official profile page, fetched once.

  profile_pass_people_directory.py fetch  --names <json list> --out <json>   fetch (network: run on Slurm) and parse; the page is kept in captures/epfl.sqlite
  profile_pass_people_directory.py parse  --names <json list> --out <json>   parse the stored pages only (no network)
  profile_pass_people_directory.py register --profiles <fetch out> --sites <sites outs> --src <register> --out <register>   write the DECISIONS rows below
  profile_pass_people_directory.py sites  --names <json {pi: url}> --out <json>   fetch each profile-linked website's front page once (https form of the linked URL;
                                                                 a redirect is recorded, never followed) and report status, sha256 and whether it names the PI

Per name the output has url, status, sha256, fetched_at, h1 (the name the page carries), positions [{title, unit_line, crumb, websites}], websites (all
anchors under a 'Website:' label), contact_links (the btn links under the name). A page counts as the PI's own only when its <h1> carries the surname.
"""
import argparse
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import school_web as W  # noqa: E402
import stage_gate as G  # noqa: E402

KEY = 'epfl'
GAP = 3.0


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()


def slug_of(name, profile_url):
    if profile_url:
        return profile_url.rstrip('/').rsplit('/', 1)[-1].split('?')[0]
    parts = [re.sub(r"[^a-z-]", '', p) for p in fold(name).split()]
    return f'{parts[0]}.{parts[-1]}'


def url_of(slug):
    return f'https://people.epfl.ch/{slug}?lang=en'


TITLE = re.compile(r'<p class="title"><strong>(.*?)</strong>(?:,\s*<span[^>]*>(.*?)</span>)?', re.S)
CRUMB = re.compile(r'search\.epfl\.ch/\?filter=unit&amp;acro=([^"&]+)"')
ANCH = re.compile(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def clean(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()


def parse(raw):
    h1 = re.search(r'<h1>(.*?)</h1>', raw, re.S)
    out = dict(h1=clean(h1.group(1)) if h1 else None, positions=[], websites=[], contact_links=[])
    head = raw[:raw.find('<p id=\'ext_data_links\'')] if "<p id='ext_data_links'" in raw else raw[:4000]
    for href, text in ANCH.findall(head[head.find('<h1>'):]):
        if not href.startswith('mailto:') and href.startswith('http'):
            out['contact_links'].append(dict(href=html.unescape(href), text=clean(text)))
    chunks = re.split(r'(?=<button class="collapse-title)', raw)
    for ch in chunks[1:]:
        m = TITLE.search(ch)
        if not m:
            continue
        crumb = CRUMB.findall(ch)
        webs = []
        for w in re.finditer(r'Website:\s*</span>\s*<a href="([^"]+)"', ch):
            webs.append(html.unescape(w.group(1)))
        place = re.search(r'itemprop="name">(.*?)</strong>', ch, re.S)
        out['positions'].append(dict(title=clean(m.group(1)), unit_line=clean(m.group(2) or ''), place=clean(place.group(1)) if place else None,
                                     crumb=[c for c in crumb], websites=webs))
        out['websites'] += webs
    out['websites'] = list(dict.fromkeys(out['websites']))
    return out


def run(names, out_path, fetch):
    pis = {x['name']: x for x in G.pis_of(KEY)}   # the census PIs (dated census + reviewed additions)
    c = W.con(KEY)
    res = {}
    for n in names:
        x = pis.get(n) or {}
        slug = slug_of(n, x.get('profile_url'))
        url = url_of(slug)
        row = dict(name=n, url=url)
        if fetch:
            r = W.live(c, url, min_delay=GAP)
        else:
            r = None
        db = c.execute('select status, sha256, fetched_at from live where url=?', (url,)).fetchone()
        if not db:
            row.update(status=None, note='not fetched (robots disallow, blocked host, or not requested)')
            res[n] = row
            continue
        row.update(status=db[0], sha256=db[1], fetched_at=db[2])
        if db[0] == 200:
            raw = W.live_html(c, url)
            p = parse(raw)
            sur = fold(n.split()[-1])
            row.update(p)
            row['names_pi'] = bool(p['h1'] and sur in fold(p['h1']))
        res[n] = row
        print(n, row.get('status'), row.get('names_pi'), flush=True)
    Path(out_path).write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')


SCHOOLS = {'IC': 'School of Computer and Communication Sciences (IC)', 'SB': 'School of Basic Sciences (SB)', 'STI': 'School of Engineering (STI)',
           'SV': 'School of Life Sciences (SV)', 'ENAC': 'School of Architecture, Civil and Environmental Engineering (ENAC)',
           'CDM': 'College of Management of Technology (CDM)'}
# an institute is named only when the charter's [census].home_units has that exact school-institute name (as for the 24 names of fbce2aea); IC stays school-level
INSTITUTES = {('STI', 'IEM'): 'Institute of Electrical and Micro Engineering (IEM)', ('SB', 'IPHYS'): 'Institute of Physics (IPHYS)',
              ('SB', 'MATH'): 'Institute of Mathematics (MATH)', ('SB', 'ISIC'): 'Institute of Chemical Sciences and Engineering (ISIC)',
              ('ENAC', 'IIC'): 'Civil Engineering Institute (IIC)', ('ENAC', 'IIE'): 'Environmental Engineering Institute (IIE)',
              ('ENAC', 'IA'): 'Institute of Architecture (IA)', ('SV', 'BMI'): 'Brain Mind Institute (BMI)', ('STI', 'IGM'): 'Institute of Mechanical Engineering (IGM)',
              ('CDM', 'MTEI'): 'Management of Technology & Entrepreneurship Institute (MTEI)', ('CDM', 'SFI'): 'Swiss Finance Institute (SFI)'}
PROFESSORIAL = re.compile(r'professor|scientist|lecturer|researcher|head of unit|chair\b', re.I)
NOT_A_LAB = re.compile(r'Teaching|Administration|Committee|Council|Steering', re.I)


def unit_name(school, inst):
    base = SCHOOLS[school]
    return f'{base} \u2014 {INSTITUTES[(school, inst)]}' if (school, inst) in INSTITUTES else base


def position_quote(flat, p):
    """A verbatim stretch of the page text from the position's title to the end of its EPFL breadcrumb."""
    head = f"{p['title']}, {p['unit_line']}"
    start = flat.find(head)
    crumb = 'EPFL \u203a ' + ' \u203a '.join(p['crumb'][1:])
    end = flat.find(crumb, start) + len(crumb) if start >= 0 else -1
    if start < 0 or end < len(crumb):
        return None
    q = flat[start:end]
    return q


def homes(names, out_path):
    """Reviewed home_department decisions (census-overrides-school.json shape) from the stored profile pages: the home is the school (and, where the
    charter names it, the institute) of the PI's professorial lab or department positions, read from each position's own EPFL breadcrumb; teaching,
    administration and committee positions never decide a home; two or more schools with no page statement of a primary -> primary_unresolved (R-HOME-01)."""
    c = W.con(KEY)
    out, held = {}, {}
    for n in names:
        pi = next(x for x in G.pis_of(KEY) if x['name'] == n)
        url = url_of(slug_of(n, pi.get('profile_url')))
        r = c.execute('select status, sha256 from live where url=?', (url,)).fetchone()
        if not r or r[0] != 200:
            held[n] = f'profile page not fetched (HTTP {r[0] if r else None})'
            continue
        raw = W.live_html(c, url)
        pr = parse(raw)
        if not (pr['h1'] and fold(n.split()[-1]) in fold(pr['h1'])):
            held[n] = f"page names {pr['h1']!r}, not the PI"
            continue
        _, _, blocks = W.live(c, url)
        flat = W.flat(blocks)
        units, ev = [], []
        for p in pr['positions']:
            if len(p['crumb']) < 3 or p['crumb'][1] not in SCHOOLS or NOT_A_LAB.search(p['unit_line']) or not PROFESSORIAL.search(p['title']):
                continue
            name = unit_name(p['crumb'][1], p['crumb'][2])
            q = position_quote(flat, p)
            if q and name not in units:
                units.append(name)
                ev.append(dict(url=url, sha256=r[1], quote=q))
        if not units:
            held[n] = 'no professorial lab or department position under a school breadcrumb on the page'
            continue
        d = dict(home_department=units[0], home_department_evidence=ev,
                 why_home_department='2026-11-15: PI profile fetched live from people.epfl.ch (robots honoured); the first professorial position\'s breadcrumb names the school'
                 + (f'; the page also places a lab position under {len(units) - 1} other school(s) and states no primary (R-HOME-01 primary_unresolved)' if len(units) > 1 else ''))
        if len(units) > 1:
            d['primary_unresolved'] = units
        out[n] = d
    Path(out_path).write_text(json.dumps(dict(decisions=out, held=held), indent=1, ensure_ascii=False) + '\n')
    print(len(out), 'decisions;', len(held), 'held')


def project_homes(overrides_path, src_path, out_path):
    """Apply the reviewed home decisions (R-HOME-01, home_departments_school.apply_reviewed_homes) to the school's home register: a PI with no row yet
    gets a hold row first (written, never a placeholder home), then the decision accepts it. The register is untracked derived data; the decisions are the tracked source."""
    from home_departments_school import apply_reviewed_homes  # noqa: E402
    rows = json.loads(Path(src_path).read_text())
    have = {r['name'] for r in rows}
    ov = json.loads(Path(overrides_path).read_text())
    for x in G.pis_of(KEY):
        if x['name'] not in have and x['name'] in ov:
            b = x.get('pi_basis') or {}
            rows.append(dict(school=KEY, name=x['name'], home_department=None, also=[], no_academic_department=False, status='hold', home_basis=None,
                             evidence=dict(url=b.get('url'), sha256=b.get('sha256'), quote=b.get('quote')), note='no home evidenced before the profile pass'))
    apply_reviewed_homes(rows, ov, lambda u: u)
    Path(out_path).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(len(rows), 'rows;', sum(r['status'] == 'accepted' for r in rows), 'accepted')


def sites(pairs, out_path):
    c = W.con(KEY)
    res = {}
    for n, url in pairs.items():
        fetch_url = re.sub(r'^http://', 'https://', url)
        r = W.live(c, fetch_url, min_delay=GAP)
        db = c.execute('select status, sha256, fetched_at from live where url=?', (fetch_url,)).fetchone()
        row = dict(name=n, linked_url=url, url=fetch_url)
        if not db:
            row.update(status=None, note='not fetched (robots disallow or blocked host)')
        else:
            row.update(status=db[0], sha256=db[1], fetched_at=db[2])
            if db[0] == 200 and r:
                flat = W.flat(r[2])
                sur = fold(n.split()[-1])
                i = fold(flat).find(sur)
                row['names_pi'] = i >= 0
                row['quote'] = flat[max(0, i - 60):i + 100] if i >= 0 else flat[:160]
                row['title'] = flat[:100]
        res[n] = row
        print(n, row.get('status'), row.get('names_pi'), flush=True)
    Path(out_path).write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')


# --- website register (stage-3 gate, 2026-11-15) ---------------------------------------------------------------------------------------------------
# Reviewed decisions, one per PI whose official profile was fetched live. 'site': the profile itself links the website (a lab position's own `Website:`
# field or the PI's contact button), recorded as a school_profile_link; 'absence': the fetched profile links no lab or personal site. A PI whose profile
# cannot be fetched, whose page names someone else, whose linked site is shared with another PI's lab, sits behind a robots refusal or at another
# institution, or whose site is only an archive, is NOT in this table: the PI stays held.
SITE = 'site'
ABSENCE = 'absence'
DECISIONS = {
    'Alcherio Martinoli': dict(kind=SITE, linked='https://disal.epfl.ch/', code='lab_site', target='https://www.epfl.ch/labs/disal/'),
    'Alexandre Alahi': dict(kind=SITE, linked='https://vita.epfl.ch/', code='lab_site', target='https://www.epfl.ch/labs/vita/'),
    'Andrés Cristi': dict(kind=SITE, linked='https://sites.google.com/view/andres-cristi', code='pi_homepage_only_no_lab_site'),
    'Bryan Ford': dict(kind=SITE, linked='http://bford.info/', code='pi_homepage_only_no_lab_site'),
    'Damir Filipovic': dict(kind=SITE, linked='https://www.epfl.ch/labs/csf/', code='lab_site'),
    'Devis Tuia': dict(kind=SITE, linked='https://www.epfl.ch/labs/eceo/', code='lab_site'),
    'Giuseppe Carleo': dict(kind=SITE, linked='https://www.epfl.ch/labs/cqsl/', code='lab_site'),
    'Ken Holstein': dict(kind=SITE, linked='https://www.thecoalalab.com/kenholstein', code='pi_homepage_only_no_lab_site'),
    'Mario Paolone': dict(kind=SITE, linked='https://desl-pwrs.epfl.ch', code='lab_site', target='https://www.epfl.ch/labs/desl/'),
    'Negar Kiyavash': dict(kind=SITE, linked='https://www.epfl.ch/labs/ban/', code='lab_site'),
    'Pascal Fua': dict(kind=SITE, linked='https://cvlab.epfl.ch/', code='lab_site', target='https://www.epfl.ch/labs/cvlab/'),
    'Pierre Vandergheynst': dict(kind=SITE, linked='https://lts2.epfl.ch/', code='lab_site'),
    'Volkan Cevher': dict(kind=SITE, linked='https://lions.epfl.ch', code='lab_site', target='https://www.epfl.ch/labs/lions/'),
    'Dimitar Jetchev': dict(kind=SITE, linked='https://tan.epfl.ch', code='lab_site', target='https://www.epfl.ch/labs/tan/'),
    'Kamiar Aminian': dict(kind=SITE, linked='http://lmam.epfl.ch', code='lab_site', target='https://www.epfl.ch/labs/lmam/'),
    'Matthieu Wyart': dict(kind=SITE, linked='https://pcsl.epfl.ch/', code='lab_site', target='https://www.epfl.ch/labs/pcsl/'),
    'Michel Bierlaire': dict(kind=SITE, linked='https://transp-or.epfl.ch/', code='lab_site', target='https://www.epfl.ch/labs/transp-or/'),
    'Sofia Olhede': dict(kind=SITE, linked='https://www.epfl.ch/labs/sds/', code='lab_site'),
    'Anne-Florence Bitbol': dict(kind=SITE, linked='https://www.epfl.ch/labs/bitbol-lab/', code='lab_site'),
    'Alessandro Chiesa': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the teaching sections ssc.epfl.ch and sin.epfl.ch only'),
    'Tanja Käser': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the teaching sections ssc.epfl.ch and sin.epfl.ch and the EPFL PhD page only'),
    'Nicolas Flammarion': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the teaching sections ssc.epfl.ch and sin.epfl.ch, the EDIC page and a Google Scholar profile (an identity index, not a site)'),
    'Andrea Cavallaro': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the school page sti.epfl.ch only'),
    'Marco Picasso': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the teaching section sma.epfl.ch only'),
    'Eduardo Moraud': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='the school pages sti.epfl.ch and sv.epfl.ch/education only'),
    'Christian Enz': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='nothing (no Website field, no contact link)'),
    'Hannes Bleuler': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='nothing (no Website field, no contact link)'),
    'Pierre-André Farine': dict(kind=ABSENCE, code='profile_only_no_homepage', seen='nothing (no Website field, no contact link)'),
    'Alfio Quarteroni': dict(kind=ABSENCE, code='site_at_other_institution', seen='only his page at Politecnico di Milano (mox.polimi.it)'),
}
STALE = ('url', 'kind', 'sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'verified', 'verified_by', 'verification_reason',
         'verification_quote', 'unverified_reason', 'official_link_status', 'official_link_evidence', 'rejected_url', 'rejected_reason', 'review_note', 'website_note')
SCOPE = 'Recorded search/access outcome; not proof no website exists or that an archive has no capture.'


def utc_of(local):
    """The live table stamps fetched_at in the node's local time (America/New_York); the registers keep UTC."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%S+00:00')


def register(profiles_path, sites_paths, reg_in, reg_out):
    prof = json.loads(Path(profiles_path).read_text())
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
        for k in STALE:
            r.pop(k, None)
        prof_at = utc_of(p['fetched_at'])
        checks = [c for c in (r.get('checks') or []) if not (c.get('source') in ('school_profile', 'school_profile_link') and c.get('at') == prof_at)]
        checks.append(dict(source='school_profile', url=p['url'], at=prof_at, result='ok', sha256=p['sha256']))
        places = set(r.get('places_checked') or []) | {'school_profile:ok'}
        if dec['kind'] == ABSENCE:
            places.add('school_profile_link:none')
            r.update(status='none_found', reason_code=dec['code'], coverage='reason', reason_type='profile_fetched_no_lab_link', reason_scope=SCOPE,
                     reason=(f"The PI's official people.epfl.ch profile ({p['url']}) was fetched live on {prof_at[:10]} (robots honoured, no archive.org) and links no lab or personal "
                             f"website (it shows {dec['seen']}); no other source was read in this pass. " + SCOPE),
                     upstream_audit_reason='only the department profile exists; it links no homepage or lab site', evidence_gaps=[])
            r.pop('rejected_reason', None)
        else:
            s = next(x for x in fetched[n] if x['status'] == 200 and (x['url'] == dec.get('target', dec['linked']) or x['url'] == re.sub(r'^http://', 'https://', dec['linked'])))
            url = dec['linked']
            anchor_ok = any(w.rstrip('/') == url.rstrip('/') for w in p['websites']) or any(c['href'].rstrip('/') == url.rstrip('/') for c in p['contact_links'])
            assert anchor_ok, (n, url)
            link = dict(source='school_profile_link', url=url, on=p['url'], at=prof_at, result='listed', anchor=url, linked_url=url,
                        source_sha256=p['sha256'], source_capture_url=None, provenance='live_profile_fetch_2026-11-15')
            cand = dict(source='candidate_site', url=url, at=utc_of(s['fetched_at']), via='school_profile_link', sha256=s['sha256'],
                        result='ok' if s['names_pi'] else 'does_not_name_pi_kept_strong_source')
            if s['url'] != url:
                cand['final_url'] = s['url']
            checks += [link, cand]
            places |= {'school_profile_link:listed', 'candidate_site:' + cand['result']}
            host = urlsplit(url).netloc
            people = next((c['url'] for c in checks if c.get('result') == 'recorded_people_page'
                           and (c['url'].startswith(s['url'].rstrip('/')) or (host != 'www.epfl.ch' and urlsplit(c['url']).netloc == host))), None)
            r.update(status='found', reason_code=dec['code'], coverage='website', url=url, kind='lab_site' if dec['code'] == 'lab_site' else 'pi_homepage',
                     found_via='school_profile_link', listed_on=p['url'], sha256=s['sha256'],
                     evidence=dict(url=s['url'], sha256=s['sha256'], quote=s['quote']), official_link_status='recorded', official_link_evidence=[link],
                     reason='Captured lab/group website.' if dec['code'] == 'lab_site' else "no lab site; the PI's own homepage is the lab page",
                     upstream_audit_reason='the PI\'s own official profile links this site (fetched live 2026-11-15)', evidence_gaps=[])
            if people:
                r['people_page'] = people
            if not s['names_pi']:
                r['unverified_reason'] = 'the front page does not carry the PI name; the PI\'s own official profile links it as the website of their lab position'
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
    ap.add_argument('cmd', choices=['fetch', 'parse', 'sites', 'homes', 'project-homes', 'register'])
    ap.add_argument('--names', help='fetch/parse/homes: a JSON list of PI names; sites: {PI: url}; project-homes: the reviewed overrides file')
    ap.add_argument('--sites', nargs='*', default=[], help='register: the sites outputs')
    ap.add_argument('--profiles', help='register: the fetch output')
    ap.add_argument('--src', help='project-homes: the home register to start from')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'register':
        register(a.profiles, a.sites, a.src, a.out)
    elif a.cmd == 'project-homes':
        project_homes(a.names, a.src, a.out)
    elif a.cmd == 'homes':
        homes(json.loads(Path(a.names).read_text()), a.out)
    elif a.cmd == 'sites':
        sites(json.loads(Path(a.names).read_text()), a.out)
    else:
        run(json.loads(Path(a.names).read_text()), a.out, a.cmd == 'fetch')


if __name__ == '__main__':
    main()
