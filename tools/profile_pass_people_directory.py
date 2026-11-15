"""EPFL stage-3 profile pass (2026-11-15): one live people.epfl.ch profile page per PI, robots honoured, >= 3 s between requests, no archive.org.

Why: the stage-3 gate for EPFL lacks (a) a reviewed home department for PIs whose census row names no school (the home is the school/institute of
the profile position's unit, read from the page's own breadcrumb EPFL > SCHOOL > INSTITUTE > UNIT) and (b) official-link / absence records for lab
websites. Both are read from the PI's own official profile page, fetched once.

  profile_pass_people_directory.py fetch  --names <json list> --out <json>   fetch (network: run on Slurm) and parse; the page is kept in captures/epfl.sqlite
  profile_pass_people_directory.py parse  --names <json list> --out <json>   parse the stored pages only (no network)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['fetch', 'parse', 'sites', 'homes', 'project-homes'])
    ap.add_argument('--names', help='fetch/parse/homes: a JSON list of PI names; sites: {PI: url}; project-homes: the reviewed overrides file')
    ap.add_argument('--src', help='project-homes: the home register to start from')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.cmd == 'project-homes':
        project_homes(a.names, a.src, a.out)
    elif a.cmd == 'homes':
        homes(json.loads(Path(a.names).read_text()), a.out)
    elif a.cmd == 'sites':
        sites(json.loads(Path(a.names).read_text()), a.out)
    else:
        run(json.loads(Path(a.names).read_text()), a.out, a.cmd == 'fetch')


if __name__ == '__main__':
    main()
